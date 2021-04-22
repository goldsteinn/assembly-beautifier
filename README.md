## x86 Assembly Beautifier


#### Features
- Style is roughly equivilent to what glibc requires
- Not robustly tested (only tested at all on at&t syntax)
- Absolutely no gurantees 
- Totally useless error message




#### Emacs (Stolen from [yapfify](https://github.com/JorisE/yapfify))

**Note expects to find executable named `asm_beautifier.py` somewhere on `PATH`.**

- Two APIS
- `abfify-region`
    - Will format highlighted text (will disable `Padd_Indent`).
- `abfify-buffer`
    - Will format entire buffer
    
Something along the lines of:

```
(add-to-list 'load-path "/path/to/abfify.el")
(require 'abfify)
```

in `.emacs` should do the trick

#### Python

- `asm_beautifier.py` can be called from command line and will format a file or stdin
- `-l` for stdin
- `--file` for file

#### Config

- Stored as json
- Default path: `/path/to/home/.config/abf.json` **Note to use dynamic config must actually specify path to home. There is a bug in `abfify.el` that requires that**.
- Possible variables:
    - "Width": <Integer, set at value for max comment length for wrapping comments. -1 will disable wrapping comments. Default = 70>
    - "Objdump_Verify": <Boolean, set if you want to compare result of objdump before and after formatting before writing over buffer to make sure no bugs>
    - "Backup_Path": <If you are rightly so afraid this program might delete your file / w.e this will copy your file before doing anything else>
    - "Backup": <Boolean to specify if you want to use this backup path feature>
    - "Padd_Indent": <Boolean set if you want to indent #ifdef / #endif / etc...>
```
    // True
    #ifdef A
    # ifdef B
    # endif
    #endif
    
    // False
    #ifdef A
    #ifdef B
    #endif
    #endif
```
    - "Init_Indent": <Int set as initial padding>
```
    // 1
    # ifdef A
    # endif
    
    // 2
    #  ifdef A
    #  endif A
    
    // 0
    #ifdef A
    #endif
```

Example config:
```
{
    "Backup_Path": "/home/noah/.tmp/asm_beautifier/",
    "Backup": "True",
    "Padd_Indent": "True",
    "Init_Indent": "1",
    "Objdump_Verify": "False"
}
```
