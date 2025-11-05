# /usr/env/sh

STARTUP_TIMEOUT=60
HEALTH_INTERVAL=10
MAX_ATTEMPTS=(($STARTUP_TIMEOUT - $HEALTH_INTERVAL) / $HEALTH_INTERVAL)

$n8n = @{
  name = 'n8n.service'
  path = (get-command 'n8n').source
  root = (join-path $psscriptroot '..')
}

function get_n8n_processes() {
      get-process 'node' -erroraction silentlycontinue |
          where-object commandline -like '*n8n*' | where-object commandline -notlike '*task*'
}

function is_n8n_running() { !!"$(get_n8n_processes)" }

function start_n8n_process() {
    start-process -filepath $n8n.path -workingdirectory $n8n.root
}

$script = join-path $psscriptroot 'service.ps1'
$procs = $(get_n8n_processes)
$running = $(is_n8n_running)

switch ($action) {
  'start' { 
    if ($procs) { return '[n8n] service is already running' }
    
    write-output '[n8n] starting service...'
    
    start_n8n_process
    start-sleep $HEALTH_INTERVAL
    
    $running = $(is_n8n_running)
    
    if ($running) { 
      return "[n8n] service started successfully" 
    }
    else { 
      write-output '[n8n] service is not yet ready' 
    }
    
    $count = 0

    while (!$running -and ($count -lt $MAX_ATTEMPTS)) {
      $running = $(is_n8n_running)
      $count += 1
      
      if ($running) { return "[n8n] service started successfully" } 
      
      write-output "[n8n] waiting for process (attempt: ${count}/${MAX_ATTEMPTS})"
      start-sleep $HEALTH_INTERVAL          
    }
    
    if (!$running) { write-output '[n8n] service startup was unsuccessful' }
  }
  'stop' { 
    if ($procs) { $procs | % { $psitem.kill() ; $psitem.waitforexit() } ; write-output 'service terminated' }
    else { write-output 'service is not running' }
  }
  'reload' { 
    & $script stop | out-null ; start-sleep $HEALTH_INTERVAL ; & $script start | out-null
  }
  'status' {
    if ($procs) { $procs | write-output } else { return '[n8n] service is down' } 
  }
  'poll' {
    while ($true) { get_n8n_processes | write-output ; start-sleep $HEALTH_INTERVAL }
  }
  'monitor' {
    while ($true) {
      $running = $(is_n8n_running)
      if (!$running) { 
        write-output '[n8n] service not detected; attempting reload'
        & $script reload ; start-sleep $STARTUP_TIMEOUT 
      }
      start-sleep $HEALTH_INTERVAL 
    }
  }
}
