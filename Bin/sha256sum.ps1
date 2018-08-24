$items = Get-ChildItem -Path . -Attributes !Directory -Exclude *.txt,*.ps1,*.gitignore -Recurse
foreach ($item in $items)
{
	$hash = Get-FileHash -Path $item.FullName -Algorithm SHA256
	$relativePath = Get-Item $item.FullName | Resolve-Path -Relative
	
	"$($hash.Hash) $relativePath"
}
