Command Line
============

Restkit integrate a simple HTTP client in command line named `restcli` allowing  you to perform requests.

Usage::

  $ restcli --help
  Usage: 'restcli [options] url [METHOD] [filename]'

  Options:
    -H HEADERS, --header=HEADERS
                          http string header in the form of Key:Value. For
                          example: "Accept: application/json"
    -i FILE, --input=FILE
                          the name of the file to read from
    -o OUTPUT, --output=OUTPUT
                          the name of the file to write to
    --follow-redirect     
    --version             show program's version number and exit
    -h, --help            show this help message and exit
  