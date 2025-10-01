[string]$pwshPath = join-path 'c:\' 'program files/powershell/7-preview/pwsh.exe'
& $pwshPath -c @"
if (test-command 'node.exe') {
    [string]`$serve_script = join-path $psscriptroot 'serve-n8n.mjs'
    `$arguments = @(`$serve_script, `$null, `$null)
    $args.CopyTo(`$arguments, 1)
    start-process -filepath node.exe -argumentlist `$arguments -nonewwindow -wait -passthru | out-null
} else { write-error 'node.exe is not on PATH' }
"@