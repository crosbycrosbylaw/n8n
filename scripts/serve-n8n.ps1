if (get-command 'node.exe' -erroraction silentlycontinue) {
    [string]$serve_script = join-path $psscriptroot 'serve-n8n.mjs'
    [string[]]$arguments = @($serve_script, $args[0], $args[1])
    start-process -filepath node.exe -argumentlist $arguments -nonewwindow -wait -passthru | out-null
} else { write-error 'node.exe is not on PATH' }