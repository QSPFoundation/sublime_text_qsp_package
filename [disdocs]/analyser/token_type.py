from enum import Enum

class QspTokenType(Enum):
    ### KEYWORDS ###
    # function_name
    DESC
    MOD
    MAX
    MIN
    RAND
    RND
    VAL
    IIF
    DYNEVAL
    FUNC
    INPUT
    USRTXT
    USER_TEXT
    MAINTXT
    STATTXT
    GETOBJ
    COUNTOBJ
    SELOBJ
    CURLOC
    CUROBJS
    SELACT
    CURACTS
    ARRSIZE
    ARRTYPE
    ARRITEM
    ARRPACK
    ARRPOS
    ARRCOMP
    INSTR
    ISNUM
    TRIM
    UCASE
    LCASE
    LEN
    MID
    REPLACE
    STR
    STRCOMP
    STRFIND
    STRPOS
    ISPLAY
    RGB
    MSECSCOUNT
    QSPVER
