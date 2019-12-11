import os
import re
import subprocess
import shutil
import json
from collections import namedtuple

from win32api import GetFileVersionInfo, LOWORD, HIWORD

script_dir = os.path.dirname(os.path.realpath(__file__))

BinPdbPair = namedtuple('BinPdbPair', [ 'bin_path', 'pdb_path' ])


def get_pe_version(path):
    info = GetFileVersionInfo(path, "\\")
    ms = info['FileVersionMS']
    ls = info['FileVersionLS']
    return '{}.{}.{}.{}'.format(HIWORD(ms), LOWORD(ms), HIWORD(ls), LOWORD(ls))


def main():
    #
    # Fetch all PDB files.
    #
    print('Downloading PDB files...')
    os.makedirs(os.path.join(script_dir, 'PDB'), exist_ok=True)

    out = subprocess.getoutput(
        r'tools\symchk.exe /r "{}" /s '
        r'SRV*{}*http://msdl.microsoft.com/download/symbols '
        r'/v '
        r'2>&1 >NUL'.format(os.path.join(script_dir, 'Bin'),
                            os.path.join(script_dir, 'PDBCache'))
    )

    #
    # Create list of [bin_path, pdb_path] pairs.
    #
    bin_path = None
    pdb_path = None
    pair_list = []

    for line in out.splitlines():
        if 'ImageName:' in line:
            assert bin_path is None
            bin_path = re.findall('ImageName: (.*)', line)[0]

        if 'PDB:' in line:
            assert bin_path is not None
            assert pdb_path is None
            pdb_path = re.findall('"([^"]*)"', line)[0]

            assert pdb_path is not None
            pair_list.append(BinPdbPair(bin_path, pdb_path))

            bin_path = None
            pdb_path = None

    for pair in pair_list:
        print('"{}"'.format(pair.bin_path))
        print('    -> {}'.format(pair.pdb_path))

    #
    # Mirror directory structure of "Bin" folder to the "PDB" folder.
    #
    descriptor = {
        'version': [],
        'filename': [],
        'type': [],
    }

    version_set = set()
    filename_set = set()
    type_set = set()

    descriptor['type'].append({
        'key': 'ALL',
        'value': 'ALL',
        'text': 'ALL'
    })

    descriptor['type'].append({
        'key': 'ALL_SORTED',
        'value': 'ALL_SORTED',
        'text': 'ALL_SORTED'
    })

    descriptor['type'].append({
        'key': 'ALL_FUNCTIONS',
        'value': 'ALL_FUNCTIONS',
        'text': 'ALL_FUNCTIONS'
    })

    for pair in pair_list:
        print()
        print('{}'.format(pair.bin_path))
        print('----------------------------------------------------------------------------------')

        bin_path_basename = os.path.basename(pair.bin_path)

        if bin_path_basename not in filename_set:
            filename_set.add(bin_path_basename)
            descriptor['filename'].append({
                'key': bin_path_basename,
                'value': bin_path_basename,
                'text': bin_path_basename
            })

        pdb_path = os.path.join(
            'PDB',
            os.path.relpath(
                os.path.dirname(pair.bin_path),
                'Bin'
            ),
            bin_path_basename + '.pdb'
        )

        version = get_pe_version(pair.bin_path)
        _, system, arch, _ = pdb_path.split('\\', 3)
        version = '{}-{} ({})'.format(system, arch, version)

        if version not in version_set:
            version_set.add(version)
            descriptor['version'].append({
                'key': '{}/{}/System32'.format(system, arch),
                'value': '{}/{}/System32'.format(system, arch),
                'text': version
            })

        print('    Copying "{}"'.format(pair.pdb_path))
        print('         -> "{}"'.format(pdb_path))

        os.makedirs(os.path.dirname(pdb_path), exist_ok=True)
        shutil.copy(pair.pdb_path, pdb_path)

        dest_path = re.sub('\\\\system32\\\\drivers\\\\', '\\\\System32\\\\', pdb_path, flags=re.I)

        dest_dir = os.path.join(
            script_dir,
            'Output',
            os.path.relpath(
                os.path.dirname(dest_path),
                'PDB'
            ),
            os.path.splitext(os.path.basename(pdb_path))[0]
        )
        os.makedirs(dest_dir, exist_ok=True)

        #
        # Dump all.
        #
        print('    Creating "ALL.h"')
        if not os.path.isfile(os.path.join(dest_dir, 'ALL.h')):
            subprocess.check_output(
                r'tools\pdbex.exe * "{}" -o "{}" -k- -z- -f'.format(pdb_path, os.path.join(dest_dir, 'ALL.h'))
            )
        else:
            print('        ... already exists, skipping')

        print('    Creating "ALL_SORTED.h"')
        if not os.path.isfile(os.path.join(dest_dir, 'ALL_SORTED.h')):
            subprocess.check_output(
                r'tools\pdbex.exe * "{}" -o "{}" -k- -z- -p- -f -y'.format(pdb_path, os.path.join(dest_dir, 'ALL_SORTED.h'))
            )
        else:
            print('        ... already exists, skipping')

        print('    Creating "ALL_FUNCTIONS.h"')
        if not os.path.isfile(os.path.join(dest_dir, 'ALL_FUNCTIONS.h')):
            subprocess.check_output(
                r'tools\pdbex.exe * "{}" -o "{}" -k- -z- -n- -l- -f'.format(pdb_path, os.path.join(dest_dir, 'ALL_FUNCTIONS.h'))
            )
        else:
            print('        ... already exists, skipping')

        dest_path = os.path.join(dest_dir, 'Standalone')
        print('    Creating "Standalone\\*.h"')
        if not os.path.isdir(dest_path):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            subprocess.check_output(
                r'tools\pdbex.exe % "{}" -o "{}" -k- -z- -p-'.format(pdb_path, dest_path)
            )
        else:
            print('        ... already exists, skipping')

        print('    Creating descriptor...')
        type_list = subprocess.check_output(
            r'tools\pdbex.exe * "{}" -k- -z- -l-'.format(pdb_path)
        ).strip().splitlines()

        print('    Got {} types'.format(len(type_list)))
        for type in type_list:
            #
            # Parse string in format: 'kind _TYPENAME;'
            #
            kind, type_name = type.decode('ascii').split(' ', 1)
            type_name = type_name.rstrip(';')

            if type_name not in type_set:
                type_set.add(type_name)
                descriptor['type'].append({
                    'key': 'Standalone/' + type_name,
                    'value': 'Standalone/' + type_name,
                    'text': type_name
                })

    with open(os.path.join(script_dir, 'Output', 'descriptor.json'), 'w+') as f:
        json.dump(descriptor, f, sort_keys=True, indent=4)


if __name__ == '__main__':
    main()
