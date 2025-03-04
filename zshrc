PROMPT="%{$fg_bold[white]%}%n"
PROMPT+=" %(?:%{$fg_bold[green]%}@ :%{$fg_bold[red]%}➜ )"
PROMPT+="%{$fg[cyan]%}%~%{$reset_color%} %(?:%{$fg_bold[green]%}➜ "
export RACK_DIR=/Users/bgudna/code/other/Rack-SDK/
export PATH=$PATH:/Users/bgudna/.local/bin/
export invidious_instance="https://vid.puffyan.us" ytfz

# Autoload zsh add-zsh-hook and vcs_info functions (-U autoload w/o substition,
autoload -Uz add-zsh-hook vcs_info
# Enable substitution in the prompt.
setopt prompt_subst
# Run vcs_info just before a prompt is displayed (precmd)
add-zsh-hook precmd vcs_info
# add ${vcs_info_msg_0} to the prompt
# e.g. here we add the Git information in red  
PROMPT+='%F{cyan}${vcs_info_msg_0_}%f '
#
# Enable checking for (un)staged changes, enabling use of %u and %c
zstyle ':vcs_info:*' check-for-changes true
# Set custom strings for an unstaged vcs repo changes (*) and staged changes
zstyle ':vcs_info:*' unstagedstr ' *'
zstyle ':vcs_info:*' stagedstr ' +'
# Set the format of the Git information for vcs_info
zstyle ':vcs_info:git:*' formats       '(%b%u%c)'
zstyle ':vcs_info:git:*' actionformats '(%b|%a%u%c)'
