#!/bin/sh
set -e

# Variable
I2CBUS=$1
I2CSLAVE=$2
BASE="/var/wcs/home/"
LOGOUT=$BASE/Liteon_FW_Update_Fxn.log
TMP=$BASE/tmp.log
BMCDATA=$BASE/liteon-psu
FW_FILE=$BASE/PS21621FSECFW01.hex
IPMICMD="i2craw.exe $I2CBUS  $I2CSLAVE -w"

CHECK_VER(){
	echo -e "\n*****Current Version*****"
#        PRTDO "$IPMICMD '0x08 0xD5'"
       # PRTDO "i2craw.exe 12 0x58 -w 0x08 0xD5'"
        $IPMICMD '0x08 0xD5'
        DELAY 0.1
}

UNLOCK_PSU(){
	echo -e "\n*****Unlock PSU*****"
	$IPMICMD '0x10 0x00'
        DELAY 0.1
}

WR_ISP_KEY(){
	echo -e "\n*****Write ISP Key*****"
        $IPMICMD '0xD1 0x49 0x6E 0x56 0x65'
	DELAY 0.1
}

BOOT_PSU_OS(){
	echo -e "\n*****Boot PSU ISP OS*****"
	$IPMICMD  '0xD2 0x02'
	DELAY 2
}

RESTART(){
	echo -e "\n*****Restart PSU ISP OS*****"
        $IPMICMD  '0xD2 0x01'
        DELAY 1
}

TRANS_DATA(){
        rm -f $BMCDATA
	echo "Transfer $FW_FILE from Intel 16 format to BMC hex data..."

	cat $FW_FILE | sed '/:020000./d' | sed '/:000000.*/d' | sed 's/://g' > $TMP
	RAW=`awk 'END {print NR}' $TMP`

	for (( i=1; i<=RAW; i=i+1 ))
	do
		DATA="`head -n $i $TMP | tail -n 1`"
		STR=""
		for (( j=9; j<=40; j=j+2 ))
		do
			echo $j
			STR=" $STR `echo $DATA | cut -c $j-$(($j+1))`"
		done
                echo $RAW
		echo $STR >> $BMCDATA
	 done
}

WR_DATA(){
        echo -e "\n*****Start to Write Data*****"
	
#	TRANS_DATA

	rm -f $TMP
	RAW=`awk 'END {print NR}' $BMCDATA`
	echo "$RAW piece of data"

	for (( i=1; i<=$RAW; i=i+1 ))
	do
		echo -n "$i:"
		DATA="`head -n $i $BMCDATA | tail -n 1`"
                STR="'0xD4  0x`echo $DATA | sed 's/ / 0x/g'`'"
		echo $STR
		CMD="$IPMICMD $STR"
                echo $CMD
		eval $CMD
                if [ "$i" -eq "1" ];then DELAY 1;
		else DELAY 0.04;
		fi
        done
	rm -f $TMP
}

#WR_DATA(){
#	rm -f $TMP
#        echo "Start to Write Data..."
#	hexdump -v -e '32/1 "%02X " "\n"' $FW_FILE > $TMP
#        RAW=`awk 'END {print NR}' $TMP | sed 's/ /0x/g'`
#	echo "Totoal: $RAW"

#       for (( i=1; i<=$RAW; i=i+1 ))
#        do
#		echo -n "$i:"
#		DATA="`head -n $i $TMP | tail -n 1`"
#		STR="0x`echo $DATA | sed 's/ / 0x/g'`"
#		P$IPMICMD  0xD4 $STR"	
                #OFFSET=$(($i-1))
#                if [ "$i" -eq "1" ];then	DELAY 1.5;
#		else	DELAY 0.04;
#		fi
#        done
#	rm -f $TMP
#}

CHECK_DATA(){
        echo -e "\n*****Check response is 0x${1}*****"

	echo "$IPMICMD 0x01 0xD2"
        ret=`$IPMICMD '0x01 0xD2'`
	if [ "$ret" != " $1" ] 
	then 
		echo "$ret		[ERROR]"
		exit
	else
		echo "$ret"
	fi
	DELAY 0.25
}

REBOOT_PSU(){
        echo -e "\n*****Reboot PSU*****"
        $IPMICMD '0x00 0xD2 0x03'
        DELAY 0.25
}

PRTDO(){
	echo $1
	$1
#	if [ "$?" != "0" ]; then echo "Command FAIL!		[ERROR]"; exit; fi
}

DELAY(){
	#echo -e "delay $1 seconds ..."
	sleep 1
}

FW_UPDATE(){
	echo "[Start to Update Liteon PSU FW]"
	CHECK_VER
	UNLOCK_PSU
	WR_ISP_KEY
	BOOT_PSU_OS
	#CHECK_DATA 40
	RESTART
	WR_DATA
	#CHECK_DATA 41
	REBOOT_PSU
	CHECK_VER
}

#----------Main---------
rm -f $LOGOUT
echo "`date`"
FW_UPDATE | tee -a $LOGOUT
echo "`date`"
#----------End----------