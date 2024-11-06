#general
alias als='cd ; nano .bash_aliases'
alias ..='cd ../'
alias update='sudo apt-get update && sudo apt-get upgrade'
alias ctrs='docker ps -a'
alias ll='ls -a'
#directory speeddial
alias proj='cd ; cd project_crosbies'
#across multiple directories
alias daily='update ; proj ; dcupre ; cd'
alias dcupre='proj ; docker compose pull ; pstart'
alias pcycle='pstop ; pstart'
alias pstart='proj ; docker compose up -d ; docker compose logs -f'
alias pstop='proj ; docker compose down'
alias pupdate='proj ; dcupre'
