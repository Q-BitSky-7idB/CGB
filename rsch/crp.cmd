@REM ;@CALL	crpt.bat	/cc_shuffle	_raw.txt	_raw.cdt
@IF EXIST _raw.txt @CALL	crpt.bat -e -f _raw.txt -kf _raw.txt -o _raw.cdt
@IF NOT EXIST _raw.txt @IF EXIST _raw.cdt @CALL	crpt -d -f _raw.cdt -o _raw.txt