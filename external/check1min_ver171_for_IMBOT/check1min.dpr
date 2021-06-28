
program check1min;
{$APPTYPE CONSOLE}
{$A-}
{$D 'Program for checking definitive data set on files prepared for CD/DVD/USB/IRDS  - June 2021`'}

{ver. 1.63
- Kontrola, czy indeksy sa w zakresie 00..90 lub 999-missing
- obliczenie jaki jest percentage indeksów magnetycznych w stosunku do 8*Max_Day
- drobna poprawka aby W14 by³o równo wyswietlane, gdy cztery bajty rowne zero
ver. 1.64
- sprawdzenie czy w naglowku readme.imo jest year z linii komendy check1min
}


uses
  SysUtils,Windows,ShellApi,StrUtils,DateUtils,CRT in 'CRT.pas';

type EInOutError = class(Exception)
    ErrorCode: SmallInt;
end;

type string250 = string[250];
     string3 = string[3];
     string4 = string[4];
     string8 = string[8];
type Calc=Record
            X:real; {999999.0 - brak,
                     ENG. missing}
            Y:real; {999999.0 - brak,
                     ENG. missing}
            Z:real; {999999.0 - brak,
                     ENG. missing}
            G:real; {999999.0 - brak,
                     ENG. missing}
            lX:integer; {liczba niepustych do obliczenia sredniej,
                         ENG. number of non-missing values}
            lY:integer; {liczba niepustych do obliczenia sredniej,
                         ENG. number of non-missing values}
            lZ:integer; {liczba niepustych do obliczenia sredniej,
                         ENG. number of non-missing values}
            lG:integer; {liczba niepustych do obliczenia sredniej,
                         ENG. number of non-missing values}
          End;
type Header=Record
              W01:  string[4];        {IAGA code     eg. BOU}
              W02:  LongInt;          {Year || Julian Day     eg. 1989001 ; January 1, 1989}
              W03:  LongInt;          {Co-Latitude     (90° - Latitude) * 1000}
              W04:  LongInt;          {Longitude     East Longitude * 1000}
              W05:  LongInt;          {Elevation     elevation in metres above sea level}
              W06:  string[4];        {Orientation     HDZF or XYZF}
              W07:  string[4];        {Origin  	eg. USGS, GSC, BGS, EOPG etc.}
              W08:  LongInt;          {D Conversion  	H/3438*10000 where H=annual mean of H}
              W09:  string[4];        {Data Quality     IMAG}
              W10:  string[4];        {Instrumentation     eg. RC (Ring Core), LC (Linear Core), etc.}
              W11:  LongInt;          {K-9 Value in nT  	e.g. 750}
              W12:  LongInt;          {Digital Sample Rate (ms)  	e.g. 125}
              W13:  string[4];        {Sensor Orientation  	e.g. XYZF, HDZF}
              W14:  string[4];        {date stamp YYMM    e.g. 0710}
              W15:  LongInt;          {vacat}
              W16:  LongInt;          {vacat}
            End;



const
  monthnames:array[1..12] of string[3]=('jan','feb','mar','apr','may','jun',
  'jul','aug','sep','oct','nov','dec');


var ch_esc:char;
    Dir_iaf_str:string250;
    year_str:string250;
    IMO_str:string250;
    year:integer;
    Max_day:integer;
    code:integer;
    DosError:ShortInt;
    temp1_str:string250;
    Raport_str:string250;
    fraport:text;
    i:integer;
    IAF_present:boolean; {TRUE there are IAF files, FALSE there are not IAF files}
    yearmean_file_present:boolean;
    yearmean_EOL:integer; {0-not recognized, 1-CrLf, 2-Cr, 3-Lf}
    X_yearmean,Y_yearmean,Z_yearmean,F_yearmean:real; {odczytane z yearmean file, 999999.0 gdy nie znaleziono;
                                                       ENG. read from yearmean, 999999.0 if not found}
    H_BLV,F_BLV:real; {odczytane z pliku BLV, 999999.0 gdy nie znaleziono;
                       ENG. H & F read from the header of BLV file, 999999.0 if not found}
    BLV_present:boolean;
    BLV_EOL:integer; {0-not recognized, 1-CrLf, 2-Cr, 3-Lf}
    ReadmeIMO_present:boolean;
    ReadmeIMO_EOL:integer; {0-not recognized, 1-CrLf, 2-Cr, 3-Lf}
    Headers:array[1..366] of Header; {tablica naglowkow W01..W16;
                                      ENG. the table of headers W01..W16 in IAF files for whole year}

    XYZG_minute:array[0..31622399,1..4] of LongInt; {tablica wartosci minutowych XYZG, 999999 lub 888888 - brak;
                                                     ENG. the table of XYZF 1-min values in IAF files, 999999 or 888888 missing, probably this table is 60 times to large}

    XYZG_hour:array[0..8783,1..4] of LongInt; {tablica wartosci godzinnych XYZG, 999999 lub 888888 - brak;
                                               ENG the table of XYZG 1-hour values in IAF files, 999999 or 888888 missing}

    XYZG_day:array[1..366,1..4] of LongInt; {tablica wartosci dobowych XYZG, 999999 lub 888888 - brak;
                                             ENG. the table of 1-day XYZG in IAF files, 999999 or 888888 missing}

    XYZG_hour_calculated:array[0..8783] of Calc; {tablica wartosci godzinnych XYZG, 999999.0-brak;
                                                  ENG. the table of XYZG 1-hour values calculated from 1-min IAF files, 999999.0 missing}

    XYZG_day_calculated:array[1..366] of Calc; {tablica wartosci dobowych XYZG, 999999.0-brak;
                                                ENG. the table of XYZG 1-day values calculated from 1-min IAF files, 999999.0 missing}

    XYZG_year_calculated:Calc; {wartosci srednich rocznych XYZG, 999999.0-brak;
                                ENG. XYZC 1-year values calculated from 1-min IAF files, 999999.0 missing}

    Indices:array[1..366,1..8] of LongInt; {tablica indeksow K - 8 na dobe;
                                            ENG. the table of K indices for whole year, 8 indices per 1-day}
    temp:integer; {temporary integer}

    DailyMeans_found_problems:integer;   {number of found problems for daily means, i.e. reported in IAF files not according to IAGA/INTERMAGNET rules}
    HourlyMeans_found_problems:integer;  {number of found problems for hourly means, i.e. reported in IAF files not according to IAGA/INTERMAGNET rules}


function Exist_File(FilNam : string):boolean;
VAR DirInfo: TSearchRec;
BEGIN
  DosError:=FindFirst(FilNam, faArchive, DirInfo);
  Exist_File:=(DosError=0);
END; {Exist_File}



function Exist_Dir(FilNam : string):boolean;
VAR DirInfo: TSearchRec;
BEGIN
  DosError:=FindFirst(FilNam, faDirectory, DirInfo);
  Exist_Dir:=(DosError=0);
END; {Exist_Dir}


Function Rewer_Hex(hex4_str:string8):string8;
{reverse order in hexadecimal representation, 4 bytes}
{sztywno 4 x hexadecimal}
var t1:string8;
begin {Function Rewer_Hex}
  t1:='        ';
  t1[1]:=hex4_str[7];
  t1[2]:=hex4_str[8];
  t1[3]:=hex4_str[5];
  t1[4]:=hex4_str[6];
  t1[5]:=hex4_str[3];
  t1[6]:=hex4_str[4];
  t1[7]:=hex4_str[1];
  t1[8]:=hex4_str[2];
  Rewer_Hex:=t1;
end; {Function Rewer_Hex}



Procedure Kopiuj1(source:string250;target:string250);
{ENG. copying source file to target file}
const rozmiar=32768;
var fib{,fob}:file of byte;
    {dlug_fil_LongInt:LongInt;}
    {dlug_fil_word:word;}
    fi,fo:file;
    buf:array[1..rozmiar] of byte;
    {b:byte;}
    result:Longint;

begin {Procedure Kopiuj1; ENG. copy}
  assign(fib,source);
  reset(fib);
  {dlug_fil_LongInt:=FileSize(fib);}
  close(fib);
  {dlug_fil_word:=dlug_fil_LongInt;}
  assign(fi,source);
  assign(fo,target);
  reset(fi,1);

  rewrite(fo,1);

  while not eof (fi) do
    begin
      BlockRead(fi,buf,rozmiar,result);
      BlockWrite(fo,buf,result)
    end;
  close(fo);
  close(fi);
end; {Procedure Kopiuj1; ENG. copy}



Function Test_Spacje_OK(str:string4):boolean;
{ENG.  Where a string is shorter than four bytes, it is padded to the left with spaces.
       For example, the string "ESK" is coded as the sequence "20 45 53 4B",
       http://www.intermagnet.org/data-donnee/formats/iaf-eng.php}
var len:integer;
    temp1_str:string250;
begin {Function Test_Spacje_OK}
  Test_Spacje_OK:=False;
  temp1_str:=str;
  temp1_str:=Trim(temp1_str);
  len:=Length(temp1_str);
  case len of
    0: begin
         if ((str[1]=' ') and (str[2]=' ') and (str[3]=' ') and (str[4]=' ')) then
         Test_Spacje_OK:=TRUE;
       end;
    1: begin
         if ((str[1]=' ') and (str[2]=' ') and (str[3]=' ')) then
           Test_Spacje_OK:=TRUE;
       end;
    2: begin
         if ((str[1]=' ') and (str[2]=' ')) then
           Test_Spacje_OK:=TRUE;
       end;
    3: begin
         if (str[1]=' ') then
           Test_Spacje_OK:=TRUE;
       end;
    4: begin
         Test_Spacje_OK:=TRUE;
       end;
  end;
end; {Function Test_Spacje_OK}



FUNCTION Leading_Zero(n:integer;nd:SmallInt):string250;
    {
    |--------------------------------------------------|
    | Zwraca string odpowiadajacy n z wiodacymi zerami |
    | Liczba cyfr razem z zerami wynosi nd             |
    | ENG. returns string with leading zeros,          |
    |      total number of digits together             |
    |      with zeros is nd                            |
    |--------------------------------------------------|
    }
  VAR
    st:STRING[200];
    i:Longint;
  BEGIN {FUNCTION Leading_Zero}
    Str(n:nd,st);
    for i:=1 to length(st) do
      begin
        if st[i]=' ' then
          st[i]:='0';
      end;
    Leading_Zero:=st;
  END; {FUNCTION Leading_Zero}



  FUNCTION Leading_Space(n:integer;nd:SmallInt):string250;
    {
    |----------------------------------------------------|
    | Zwraca string odpowiadajacy n z wiodacymi spacjami |
    | Liczba cyfr razem ze spacjami wynosi nd            |
    | ENG. returns string with leading spaces,           |
    |      total number of digits together               |
    |      with spaces is nd                             |
    |----------------------------------------------------|
    }
  VAR
    st:STRING[200];
    i:Longint;
  BEGIN {FUNCTION Leading_Space}
    Str(n:nd,st);
    for i:=1 to length(st) do
      begin
        if st[i]=' ' then
          st[i]:=' ';
      end;
    Leading_Space:=st;
  END; {FUNCTION Leading_Space}



Function Wytnij(wiersz:string250; kan:integer):string250;
   {-----------------------------------------------------------------|
   | kan=0 oznacza 1-szy ciag znakow                                 |
   | ENG. returns a piece of string from string wiersz               |
   |      eg. wiersz=' 1975.500  -0 36.2  64 45.9  20273', kan=2     |
   |          returns '36.2'                                         |
   |-----------------------------------------------------------------}
var i,i1,i2:integer;
    znaleziono:integer;
    temp1_str:string250;
begin {Function Wytnij; ENG. cut/copy}
  temp1_str:=wiersz;
  insert(' ',temp1_str,1+length(temp1_str));
  if temp1_str[1]<>' ' then insert(' ',temp1_str,1);
  i:=length(temp1_str);
  while (i>=1) do
    begin
      if ((i>=2) and (temp1_str[i]=' ') and (temp1_str[i-1]=' ')) then
        delete(temp1_str,i,1);
      i:=i-1;
    end;
  wiersz:=temp1_str;

  {poszukiwanie lewej spacji;
   ENG. searching for left character space}
  znaleziono:=0;
  i:=1;
  repeat
    if wiersz[i]=' ' then znaleziono:=znaleziono+1;
    i:=i+1;
  until (znaleziono=kan+1);
  i1:=i-1;

  {poszukiwanie prawej spacji;
   ENG. searching for right space character}
  i:=i1;
  repeat
   i:=i+1;
  until ((wiersz[i]=' ') or (i>length(wiersz)));
  i2:=i;

  Wytnij:=copy(wiersz,i1+1,i2-i1-1);
end; {Function Wytnij; ENG. cut/copy}








{=====================================================================================}

procedure ymchk;

{ENG. this procedure checks yearmean file, originally this procedure was written as separate program}

{$APPTYPE CONSOLE}
{$A-}
{$D 'Program do kontroli plików definitive na DVD - April 2015`'}

{"_YYYY.yyy_DDD_dd.d_III_ii.i_HHHHHH_XXXXXX_YYYYYY_ZZZZZZ_FFFFFF_A_EEEE_NNN"}


type
  string250=string[250];
  string2=string[2];
  string1=string[1];
  string20=string[20];

const wzor_str: string250 = '_YYYY.yyy_DDD_dd.d_III_ii.i_HHHHHH_XXXXXX_YYYYYY_ZZZZZZ_FFFFFF_A_EEEE_NNN';
{ENG. wzor_str is correct pattern of yearmean line specified on http://www.intermagnet.org/data-donnee/formats/iyfv101-eng.php}

var
   DirInfo:TSearchRec;
   DosError:ShortInt;
   ch_esc:char;
   Dir_Source:string250;
   IAGA_str:string250;
   Out_str{,Raport_str}:string250;
   {year_str,year_beg_str,year_end_str:string250;}
   fyear:text;
   wiersz:string250;  {ENG. wiersz means in English line}
   temp1_str,temp2_str,temp3_str:string250;
   {fraport:text;}
   code:integer;
   nr_wiersza:integer;
   D_deg,D_min,I_deg,I_min,H_nT,F_nT,X_nT,Y_nT,Z_nT:Real48;
   Fobl,Fdelta:Real48;
   Hobl,Hobl1,Hdelta,Yobl,Ydelta:Real48;
   Zobl,Zobl1,Zdelta:Real48;
   {COD:string[5];}
   i:integer;
   year,year_beg,year_end:integer;
   year_found:array[0..100] of integer;
   e01_str,e02_str,e03_str,e04_str,e05_str,e06_str:string20;
   e07_str,e08_str,e09_str,e10_str,e11_str,e12_str,e13_str:string20;
   f:file of byte;
   byt1,byt2:byte;
   cl:integer;
   year_min,year_max:integer;
   a01_str,a02_str,a03_str,a04_str,a05_str,a06_str:string20;
   a07_str,a08_str,a09_str,a10_str,a11_str,a12_str,a13_str:string20;
   err:integer;
   file_yearmean_str:string250;


Procedure KasujPliki(Szkielet:string250);
{ENG. KasujPliki means erase files, note: this procedure erases one file only}
var fil:file;
    temp1_str:string[100];
    temp2_str:string[100];
    i:SmallInt;
    DirInfo: TSearchRec;
begin {Procedure KasujPliki}
  temp1_str:=ExpandFileName(Szkielet);
  temp2_str:=temp1_str;
  i:=length(temp2_str);
  repeat
    i:=i-1;
  until (temp2_str[i]='\');
  delete(temp2_str,i+1,length(temp2_str)-i);
  DosError:=FindFirst(temp1_str,faArchive,DirInfo);
  while (DosError=0) do
    begin
      AssignFile(fil,temp2_str+DirInfo.name);
      erase(fil);
      DosError:=FindNext(DirInfo);
    end;
end; {Procedure KasujPliki}


Procedure Text_Any_System_to_Windows(File1_str:string250; File2_str:string250);
var fil1,fil2:text;
    f1_str,f2_str:string250;
    line1,line2:string;
begin {Procedure Text_Any_System_to_Windows}
  f1_str:=ExpandFileName(File1_str);
  f2_str:=ExpandFileName(File2_str);
  AssignFile(fil1,f1_str);
  AssignFile(fil2,f2_str);
  reset(fil1);
  rewrite(fil2);
  while not eof(fil1) do
    begin
      readln(fil1,line1);
      line2:=AdjustLineBreaks(line1);
      writeln(fil2,line2);
    end;
  CloseFile(fil1);
  CloseFile(fil2);
end; {Procedure Text_Any_System_to_Windows}


Function Wytnij(wiersz:string250; kan:integer):string250;
   {-----------------------------------------------------------------|
   | kan=0 oznacza 1-szy ciag znakow                                 |
   | ENG. returns a piece of string from string wiersz               |
   |      eg. wiersz=' 1975.500  -0 36.2  64 45.9  20273', kan=2     |
   |          returns '36.2'                                         |
   |-----------------------------------------------------------------}

var i,i1,i2:integer;
    znaleziono:integer;
    temp1_str:string250;
begin {Function Wytnij; ENG. cut/copy}
  temp1_str:=wiersz;
  insert(' ',temp1_str,1+length(temp1_str));
  if temp1_str[1]<>' ' then insert(' ',temp1_str,1);
  i:=length(temp1_str);
  while (i>=1) do
    begin
      if ((i>=2) and (temp1_str[i]=' ') and (temp1_str[i-1]=' ')) then
        delete(temp1_str,i,1);
      i:=i-1;
    end;
  wiersz:=temp1_str;

  {poszukiwanie lewej spacji;
   ENG. searching for left character space}
  znaleziono:=0;
  i:=1;
  repeat
    if wiersz[i]=' ' then znaleziono:=znaleziono+1;
    i:=i+1;
  until (znaleziono=kan+1);
  i1:=i-1;

  {poszukiwanie prawej spacji;
   ENG. searching for right character space}
  i:=i1;
  repeat
   i:=i+1;
  until ((wiersz[i]=' ') or (i>length(wiersz)));
  i2:=i;

  Wytnij:=copy(wiersz,i1+1,i2-i1-1);
end; {Function Wytnij; ENG. cut/copy}


Function Wytnij_sztywno(wiersz:string250; kan:integer):string250;
   {--------------------------------------------------------------------------------------------------------------------|
   | kan=0 oznacza 1-szy ciag znakow                                                                                    |
   | ENG. returns a piece of string from string wiersz, it is assumed that wiersz is correctly formatted yearmean line  |                                                         |
   |      eg. wiersz=' 1956.500 357 45.9  67 13.4  18454  18440   -720  43949  47666 A XYZ     '   kan=7                       |
   |          returns '-720'                                                                                            |
   |--------------------------------------------------------------------------------------------------------------------}
{"_YYYY.yyy_DDD_dd.d_III_ii.i_HHHHHH_XXXXXX_YYYYYY_ZZZZZZ_FFFFFF_A_EEEE_NNN"}
{"1234567890123456789012345678901234567890123456789012345678901234567890123"}
var temp1_str:string250;
begin {Function Wytnij_sztywno; ENG. cut/copy}
  temp1_str:=wiersz;
  case kan of
     0: begin
          temp1_str:=copy(wiersz,2,8);
        end;
     1: begin
          temp1_str:=copy(wiersz,10,4);
          while not((temp1_str[1]<>' ') and (length(temp1_str)>=1)) do
            begin
              delete(temp1_str,1,1)
            end;
        end;
     2: begin
          temp1_str:=copy(wiersz,14,5);
          while not((temp1_str[1]<>' ') and (length(temp1_str)>=1)) do
            begin
              delete(temp1_str,1,1)
            end;
        end;
     3: begin
          temp1_str:=copy(wiersz,19,4);
          while not((temp1_str[1]<>' ') and (length(temp1_str)>=1)) do
            begin
              delete(temp1_str,1,1)
            end;
        end;
     4: begin
          temp1_str:=copy(wiersz,23,5);
          while not((temp1_str[1]<>' ') and (length(temp1_str)>=1)) do
            begin
              delete(temp1_str,1,1)
            end;
        end;
     5: begin
          temp1_str:=copy(wiersz,28,7);
          while not((temp1_str[1]<>' ') and (length(temp1_str)>=1)) do
            begin
              delete(temp1_str,1,1)
            end;
        end;
     6: begin
          temp1_str:=copy(wiersz,35,7);
          while not((temp1_str[1]<>' ') and (length(temp1_str)>=1)) do
            begin
              delete(temp1_str,1,1)
            end;
        end;
     7: begin
          temp1_str:=copy(wiersz,42,7);
          while not((temp1_str[1]<>' ') and (length(temp1_str)>=1)) do
            begin
              delete(temp1_str,1,1)
            end;
        end;
     8: begin
          temp1_str:=copy(wiersz,49,7);
          while not((temp1_str[1]<>' ') and (length(temp1_str)>=1)) do
            begin
              delete(temp1_str,1,1)
            end;
        end;
     9: begin
          temp1_str:=copy(wiersz,56,7);
          while not((temp1_str[1]<>' ') and (length(temp1_str)>=1)) do
            begin
              delete(temp1_str,1,1)
            end;
        end;
    10: begin
          temp1_str:=copy(wiersz,64,1);
        end;
    11: begin
          temp1_str:=copy(wiersz,65,5);
          if ((temp1_str<>'     ') and (length(temp1_str)>=1)) then
            begin
              while not((temp1_str[1]<>' ') and (length(temp1_str)>=1)) do
                begin
                  delete(temp1_str,1,1)
                end;
              while not((temp1_str[length(temp1_str)]<>' ') and (length(temp1_str)>=1)) do
                begin
                  delete(temp1_str,length(temp1_str),1)
                end;
            end
          else
            begin
              temp1_str:='';
            end;
        end;
    12: begin
          temp1_str:=copy(wiersz,70,4);
        end;
  end;
  Wytnij_sztywno:=temp1_str;
end; {Function Wytnij_sztywno; ENG. cut/copy}


Procedure Check_LineLengths;
var err:integer;
begin {Procedure Check_LineLengths}
  writeln(fraport,'LINE LENGTHS ERRORS:          (must be 73chars)');
  temp1_str:=file_yearmean_str;
  AssignFile(fyear,temp1_str);
  reset(fyear);
  nr_wiersza:=0;
  err:=0;
  while not eof(fyear) do
    begin {while not eof(fyear)}
      nr_wiersza:=nr_wiersza+1;
      readln(fyear,wiersz);
      {
      e01_str:=Wytnij(wiersz,0);
      e02_str:=Wytnij(wiersz,1);
      e03_str:=Wytnij(wiersz,2);
      e04_str:=Wytnij(wiersz,3);
      e05_str:=Wytnij(wiersz,4);
      e06_str:=Wytnij(wiersz,5);
      e07_str:=Wytnij(wiersz,6);
      e08_str:=Wytnij(wiersz,7);
      e09_str:=Wytnij(wiersz,8);
      e10_str:=Wytnij(wiersz,9);
      e11_str:=Wytnij(wiersz,10);
      e12_str:=Wytnij(wiersz,11);
      e13_str:=Wytnij(wiersz,12);
      }
      e01_str:=Wytnij(wiersz,0);
      if length(e01_str)>=5 then
        begin
          temp2_str:=copy(e01_str,1,4);
          temp3_str:=copy(e01_str,5,1);
          val(temp2_str,year,code);
          if ((code=0) and ((temp3_str='.') or (temp3_str=','))) then
            begin
              if length(wiersz)<>73 then
                begin
                  err:=err+1;
                  writeln(fraport,'   !  ',length(wiersz),'chrs "',wiersz,'"');
                end;
            end;
        end;
    end; {while not eof(fyear)}
  close(fyear);
  if err=0 then
    writeln(fraport,'      OK');
end; {Procedure Check_LineLengths}


Procedure Find_Min_Incomplete;
var i:integer;
begin {Procedure Find_Min_Incomplete}
  year_min:=2035;
  temp1_str:=file_yearmean_str;
  AssignFile(fyear,temp1_str);
  reset(fyear);
  nr_wiersza:=0;
  while not eof(fyear) do
    begin {while not eof(fyear)}
      nr_wiersza:=nr_wiersza+1;
      readln(fyear,wiersz);
      for i:=1 to length(wiersz) do
        wiersz[i]:=UpCase(wiersz[i]);
      e01_str:=Wytnij(wiersz,0);
      e02_str:=Wytnij(wiersz,1);
      e03_str:=Wytnij(wiersz,2);
      e04_str:=Wytnij(wiersz,3);
      e05_str:=Wytnij(wiersz,4);
      e06_str:=Wytnij(wiersz,5);
      e07_str:=Wytnij(wiersz,6);
      e08_str:=Wytnij(wiersz,7);
      e09_str:=Wytnij(wiersz,8);
      e10_str:=Wytnij(wiersz,9);
      e11_str:=Wytnij(wiersz,10);
      e12_str:=Wytnij(wiersz,11);
      e13_str:=Wytnij(wiersz,12);
      if length(e01_str)>=5 then
        begin
          temp2_str:=copy(e01_str,1,4);
          temp3_str:=copy(e01_str,5,1);
          val(temp2_str,year,code);
          if ((code=0) and (temp3_str='.') and (e11_str='I')) then
            begin
              if year<year_min then
                year_min:=year;
            end;
        end;
    end; {while not eof(fyear)}
  close(fyear);
end; {Procedure Find_Min_Incomplete}


Procedure Find_Max_Incomplete;
var i:integer;
begin {Procedure Find_Max_Incomplete}
  year_max:=1850;
  temp1_str:=file_yearmean_str;
  AssignFile(fyear,temp1_str);
  reset(fyear);
  nr_wiersza:=0;
  while not eof(fyear) do
    begin {while not eof(fyear)}
      nr_wiersza:=nr_wiersza+1;
      readln(fyear,wiersz);
      for i:=1 to length(wiersz) do
        wiersz[i]:=UpCase(wiersz[i]);
      e01_str:=Wytnij(wiersz,0);
      e02_str:=Wytnij(wiersz,1);
      e03_str:=Wytnij(wiersz,2);
      e04_str:=Wytnij(wiersz,3);
      e05_str:=Wytnij(wiersz,4);
      e06_str:=Wytnij(wiersz,5);
      e07_str:=Wytnij(wiersz,6);
      e08_str:=Wytnij(wiersz,7);
      e09_str:=Wytnij(wiersz,8);
      e10_str:=Wytnij(wiersz,9);
      e11_str:=Wytnij(wiersz,10);
      e12_str:=Wytnij(wiersz,11);
      e13_str:=Wytnij(wiersz,12);
      if length(e01_str)>=5 then
        begin
          temp2_str:=copy(e01_str,1,4);
          temp3_str:=copy(e01_str,5,1);
          val(temp2_str,year,code);
          if ((code=0) and (temp3_str='.') and (e11_str='I')) then
            begin
              if year>year_max then
                year_max:=year;
            end;
        end;
    end; {while not eof(fyear)}
  close(fyear);
end; {Procedure Find_Max_Incomplete}


Procedure Find_Min_All;
var i:integer;
begin {Procedure Find_Min_All}
  year_min:=2035;
  temp1_str:=file_yearmean_str;
  AssignFile(fyear,temp1_str);
  reset(fyear);
  nr_wiersza:=0;
  while not eof(fyear) do
    begin {while not eof(fyear)}
      nr_wiersza:=nr_wiersza+1;
      readln(fyear,wiersz);
      for i:=1 to length(wiersz) do
        wiersz[i]:=UpCase(wiersz[i]);
      e01_str:=Wytnij(wiersz,0);
      e02_str:=Wytnij(wiersz,1);
      e03_str:=Wytnij(wiersz,2);
      e04_str:=Wytnij(wiersz,3);
      e05_str:=Wytnij(wiersz,4);
      e06_str:=Wytnij(wiersz,5);
      e07_str:=Wytnij(wiersz,6);
      e08_str:=Wytnij(wiersz,7);
      e09_str:=Wytnij(wiersz,8);
      e10_str:=Wytnij(wiersz,9);
      e11_str:=Wytnij(wiersz,10);
      e12_str:=Wytnij(wiersz,11);
      e13_str:=Wytnij(wiersz,12);
      if length(e01_str)>=5 then
        begin
          temp2_str:=copy(e01_str,1,4);
          temp3_str:=copy(e01_str,5,1);
          val(temp2_str,year,code);
          if ((code=0) and (temp3_str='.') and (e11_str='A')) then
            begin
              if year<year_min then
                year_min:=year;
            end;
        end;
    end; {while not eof(fyear)}
  close(fyear);
end; {Procedure Find_Min_All}


Procedure Find_Max_All;
var i:integer;
begin {Procedure Find_Max_All}
  year_max:=1850;
  temp1_str:=file_yearmean_str;
  AssignFile(fyear,temp1_str);
  reset(fyear);
  nr_wiersza:=0;
  while not eof(fyear) do
    begin {while not eof(fyear)}
      nr_wiersza:=nr_wiersza+1;
      readln(fyear,wiersz);
      for i:=1 to length(wiersz) do
        wiersz[i]:=UpCase(wiersz[i]);
      e01_str:=Wytnij(wiersz,0);
      e02_str:=Wytnij(wiersz,1);
      e03_str:=Wytnij(wiersz,2);
      e04_str:=Wytnij(wiersz,3);
      e05_str:=Wytnij(wiersz,4);
      e06_str:=Wytnij(wiersz,5);
      e07_str:=Wytnij(wiersz,6);
      e08_str:=Wytnij(wiersz,7);
      e09_str:=Wytnij(wiersz,8);
      e10_str:=Wytnij(wiersz,9);
      e11_str:=Wytnij(wiersz,10);
      e12_str:=Wytnij(wiersz,11);
      e13_str:=Wytnij(wiersz,12);
      if length(e01_str)>=5 then
        begin
          temp2_str:=copy(e01_str,1,4);
          temp3_str:=copy(e01_str,5,1);
          val(temp2_str,year,code);
          if ((code=0) and (temp3_str='.') and (e11_str='A')) then
            begin
              if year>year_max then
                year_max:=year;
            end;
        end;
    end; {while not eof(fyear)}
  close(fyear);
end; {Procedure Find_Max_All}


Procedure Find_Missing_All;
var y:integer;
    year_found:integer;
    i:integer;
begin {Procedure Find_Missing_All}
  for y:=year_min to year_max do
    begin {for y:=year_min to year_max do}
      temp1_str:=file_yearmean_str;
      AssignFile(fyear,temp1_str);
      reset(fyear);
      nr_wiersza:=0;
      year_found:=0;
      while not eof(fyear) do
        begin {while not eof(fyear)}
          nr_wiersza:=nr_wiersza+1;
          readln(fyear,wiersz);
          for i:=1 to length(wiersz) do
            wiersz[i]:=UpCase(wiersz[i]);
          e01_str:=Wytnij(wiersz,0);
          e02_str:=Wytnij(wiersz,1);
          e03_str:=Wytnij(wiersz,2);
          e04_str:=Wytnij(wiersz,3);
          e05_str:=Wytnij(wiersz,4);
          e06_str:=Wytnij(wiersz,5);
          e07_str:=Wytnij(wiersz,6);
          e08_str:=Wytnij(wiersz,7);
          e09_str:=Wytnij(wiersz,8);
          e10_str:=Wytnij(wiersz,9);
          e11_str:=Wytnij(wiersz,10);
          e12_str:=Wytnij(wiersz,11);
          e13_str:=Wytnij(wiersz,12);
          if length(e01_str)>=5 then
            begin
              temp2_str:=copy(e01_str,1,4);
              temp3_str:=copy(e01_str,5,1);
              val(temp2_str,year,code);
              if ((code=0) and (temp3_str='.') and (e11_str='A')) then
                begin
                  if year=y then
                    year_found:=year_found+1;
                end;
            end;
        end; {while not eof(fyear)}
      close(fyear);
      if year_found<>1 then
        begin
          if year_found=0 then
            begin
              writeln(fraport,'   !  ',y,' not found or incomplete');
            end
          else
            begin
              writeln(fraport,'   !  ',y,' found ',year_found,' times');
            end;
        end;
    end; {for y:=year_min to year_max do}
end; {Procedure Find_Missing_All}


Procedure Find_Min_Quiet;
var i:integer;
begin {Procedure Find_Min_Quiet}
  year_min:=2035;
  temp1_str:=file_yearmean_str;
  AssignFile(fyear,temp1_str);
  reset(fyear);
  nr_wiersza:=0;
  while not eof(fyear) do
    begin {while not eof(fyear)}
      nr_wiersza:=nr_wiersza+1;
      readln(fyear,wiersz);
      for i:=1 to length(wiersz) do
        wiersz[i]:=UpCase(wiersz[i]);
      e01_str:=Wytnij(wiersz,0);
      e02_str:=Wytnij(wiersz,1);
      e03_str:=Wytnij(wiersz,2);
      e04_str:=Wytnij(wiersz,3);
      e05_str:=Wytnij(wiersz,4);
      e06_str:=Wytnij(wiersz,5);
      e07_str:=Wytnij(wiersz,6);
      e08_str:=Wytnij(wiersz,7);
      e09_str:=Wytnij(wiersz,8);
      e10_str:=Wytnij(wiersz,9);
      e11_str:=Wytnij(wiersz,10);
      e12_str:=Wytnij(wiersz,11);
      e13_str:=Wytnij(wiersz,12);
      if length(e01_str)>=5 then
        begin
          temp2_str:=copy(e01_str,1,4);
          temp3_str:=copy(e01_str,5,1);
          val(temp2_str,year,code);
          if ((code=0) and (temp3_str='.') and (e11_str='Q')) then
            begin
              if year<year_min then
                year_min:=year;
            end;
        end;
    end; {while not eof(fyear)}
  close(fyear);
end; {Procedure Find_Min_Quiet}


Procedure Find_Max_Quiet;
var i:integer;
begin {Procedure Find_Max_Quiet}
  year_max:=1850;
  temp1_str:=file_yearmean_str;
  AssignFile(fyear,temp1_str);
  reset(fyear);
  nr_wiersza:=0;
  while not eof(fyear) do
    begin {while not eof(fyear)}
      nr_wiersza:=nr_wiersza+1;
      readln(fyear,wiersz);
      for i:=1 to length(wiersz) do
        wiersz[i]:=UpCase(wiersz[i]);
      e01_str:=Wytnij(wiersz,0);
      e02_str:=Wytnij(wiersz,1);
      e03_str:=Wytnij(wiersz,2);
      e04_str:=Wytnij(wiersz,3);
      e05_str:=Wytnij(wiersz,4);
      e06_str:=Wytnij(wiersz,5);
      e07_str:=Wytnij(wiersz,6);
      e08_str:=Wytnij(wiersz,7);
      e09_str:=Wytnij(wiersz,8);
      e10_str:=Wytnij(wiersz,9);
      e11_str:=Wytnij(wiersz,10);
      e12_str:=Wytnij(wiersz,11);
      e13_str:=Wytnij(wiersz,12);
      if length(e01_str)>=5 then
        begin
          temp2_str:=copy(e01_str,1,4);
          temp3_str:=copy(e01_str,5,1);
          val(temp2_str,year,code);
          if ((code=0) and (temp3_str='.') and (e11_str='Q')) then
            begin
              if year>year_max then
                year_max:=year;
            end;
        end;
    end; {while not eof(fyear)}
  close(fyear);
end; {Procedure Find_Max_Quiet}


Procedure Find_Missing_Quiet;
var y:integer;
    year_found:integer;
    i:integer;
begin {Procedure Find_Missing_Quiet}
  for y:=year_min to year_max do
    begin {for y:=year_min to year_max do}
      temp1_str:=file_yearmean_str;
      AssignFile(fyear,temp1_str);
      reset(fyear);
      nr_wiersza:=0;
      year_found:=0;
      while not eof(fyear) do
        begin {while not eof(fyear)}
          nr_wiersza:=nr_wiersza+1;
          readln(fyear,wiersz);
          for i:=1 to length(wiersz) do
            wiersz[i]:=UpCase(wiersz[i]);
          e01_str:=Wytnij(wiersz,0);
          e02_str:=Wytnij(wiersz,1);
          e03_str:=Wytnij(wiersz,2);
          e04_str:=Wytnij(wiersz,3);
          e05_str:=Wytnij(wiersz,4);
          e06_str:=Wytnij(wiersz,5);
          e07_str:=Wytnij(wiersz,6);
          e08_str:=Wytnij(wiersz,7);
          e09_str:=Wytnij(wiersz,8);
          e10_str:=Wytnij(wiersz,9);
          e11_str:=Wytnij(wiersz,10);
          e12_str:=Wytnij(wiersz,11);
          e13_str:=Wytnij(wiersz,12);
          if length(e01_str)>=5 then
            begin
              temp2_str:=copy(e01_str,1,4);
              temp3_str:=copy(e01_str,5,1);
              val(temp2_str,year,code);
              if ((code=0) and (temp3_str='.') and (e11_str='Q')) then
                begin
                  if year=y then
                    year_found:=year_found+1;
                end;
            end;
        end; {while not eof(fyear)}
      close(fyear);
      if year_found<>1 then
        begin
          if year_found=0 then
            begin
              writeln(fraport,'   !  ',y,' not found or incomplete');
            end
          else
            begin
              writeln(fraport,'   !  ',y,' found ',year_found,' times');
            end;
        end;
    end; {for y:=year_min to year_max do}
end; {Procedure Find_Missing_Quiet}


Procedure Find_Min_Disturbed;
var i:integer;
begin {Procedure Find_Min_Disturbed}
  year_min:=2035;
  temp1_str:=file_yearmean_str;
  AssignFile(fyear,temp1_str);
  reset(fyear);
  nr_wiersza:=0;
  while not eof(fyear) do
    begin {while not eof(fyear)}
      nr_wiersza:=nr_wiersza+1;
      readln(fyear,wiersz);
      for i:=1 to length(wiersz) do
        wiersz[i]:=UpCase(wiersz[i]);
      e01_str:=Wytnij(wiersz,0);
      e02_str:=Wytnij(wiersz,1);
      e03_str:=Wytnij(wiersz,2);
      e04_str:=Wytnij(wiersz,3);
      e05_str:=Wytnij(wiersz,4);
      e06_str:=Wytnij(wiersz,5);
      e07_str:=Wytnij(wiersz,6);
      e08_str:=Wytnij(wiersz,7);
      e09_str:=Wytnij(wiersz,8);
      e10_str:=Wytnij(wiersz,9);
      e11_str:=Wytnij(wiersz,10);
      e12_str:=Wytnij(wiersz,11);
      e13_str:=Wytnij(wiersz,12);
      if length(e01_str)>=5 then
        begin
          temp2_str:=copy(e01_str,1,4);
          temp3_str:=copy(e01_str,5,1);
          val(temp2_str,year,code);
          if ((code=0) and (temp3_str='.') and (e11_str='D')) then
            begin
              if year<year_min then
                year_min:=year;
            end;
        end;
    end; {while not eof(fyear)}
  close(fyear);
end; {Procedure Find_Min_Disturbed}


Procedure Find_Max_Disturbed;
var i:integer;
begin {Procedure Find_Max_Disturbed}
  year_max:=1850;
  temp1_str:=file_yearmean_str;
  AssignFile(fyear,temp1_str);
  reset(fyear);
  nr_wiersza:=0;
  while not eof(fyear) do
    begin {while not eof(fyear)}
      nr_wiersza:=nr_wiersza+1;
      readln(fyear,wiersz);
      for i:=1 to length(wiersz) do
        wiersz[i]:=UpCase(wiersz[i]);
      e01_str:=Wytnij(wiersz,0);
      e02_str:=Wytnij(wiersz,1);
      e03_str:=Wytnij(wiersz,2);
      e04_str:=Wytnij(wiersz,3);
      e05_str:=Wytnij(wiersz,4);
      e06_str:=Wytnij(wiersz,5);
      e07_str:=Wytnij(wiersz,6);
      e08_str:=Wytnij(wiersz,7);
      e09_str:=Wytnij(wiersz,8);
      e10_str:=Wytnij(wiersz,9);
      e11_str:=Wytnij(wiersz,10);
      e12_str:=Wytnij(wiersz,11);
      e13_str:=Wytnij(wiersz,12);
      if length(e01_str)>=5 then
        begin
          temp2_str:=copy(e01_str,1,4);
          temp3_str:=copy(e01_str,5,1);
          val(temp2_str,year,code);
          if ((code=0) and (temp3_str='.') and (e11_str='D')) then
            begin
              if year>year_max then
                year_max:=year;
            end;
        end;
    end; {while not eof(fyear)}
  close(fyear);
end; {Procedure Find_Max_Disturbed}


Procedure Find_Missing_Disturbed;
var y:integer;
    year_found:integer;
    i:integer;
begin {Procedure Find_Missing_Disturbed}
  for y:=year_min to year_max do
    begin {for y:=year_min to year_max do}
      temp1_str:=file_yearmean_str;
      AssignFile(fyear,temp1_str);
      reset(fyear);
      nr_wiersza:=0;
      year_found:=0;
      while not eof(fyear) do
        begin {while not eof(fyear)}
          nr_wiersza:=nr_wiersza+1;
          readln(fyear,wiersz);
          for i:=1 to length(wiersz) do
            wiersz[i]:=UpCase(wiersz[i]);
          e01_str:=Wytnij(wiersz,0);
          e02_str:=Wytnij(wiersz,1);
          e03_str:=Wytnij(wiersz,2);
          e04_str:=Wytnij(wiersz,3);
          e05_str:=Wytnij(wiersz,4);
          e06_str:=Wytnij(wiersz,5);
          e07_str:=Wytnij(wiersz,6);
          e08_str:=Wytnij(wiersz,7);
          e09_str:=Wytnij(wiersz,8);
          e10_str:=Wytnij(wiersz,9);
          e11_str:=Wytnij(wiersz,10);
          e12_str:=Wytnij(wiersz,11);
          e13_str:=Wytnij(wiersz,12);
          if length(e01_str)>=5 then
            begin
              temp2_str:=copy(e01_str,1,4);
              temp3_str:=copy(e01_str,5,1);
              val(temp2_str,year,code);
              if ((code=0) and (temp3_str='.') and (e11_str='D')) then
                begin
                  if year=y then
                    year_found:=year_found+1;
                end;
            end;
        end; {while not eof(fyear)}
      close(fyear);
      if year_found<>1 then
        begin
          if year_found=0 then
            begin
              writeln(fraport,'   !  ',y,' not found or incomplete');
            end
          else
            begin
              writeln(fraport,'   !  ',y,' found ',year_found,' times');
            end;
        end;
    end; {for y:=year_min to year_max do}
end; {Procedure Find_Missing_Disturbed}


Procedure Discrepancy(ADQ:string1);
var y:integer;
    i:integer;
    tabul:boolean;
    b:byte;
    t1_real, t2_real:real;
begin {Procedure Discrepancy}
  for y:=year_min to year_max do
    begin {for y:=year_min to year_max do}
      temp1_str:=file_yearmean_str;
      AssignFile(fyear,temp1_str);
      reset(fyear);
      nr_wiersza:=0;
      while not eof(fyear) do
        begin {while not eof(fyear)}
          nr_wiersza:=nr_wiersza+1;
          readln(fyear,wiersz);
          for i:=1 to length(wiersz) do
            wiersz[i]:=UpCase(wiersz[i]);
          e01_str:=Wytnij(wiersz,0);
          e02_str:=Wytnij(wiersz,1);
          e03_str:=Wytnij(wiersz,2);
          e04_str:=Wytnij(wiersz,3);
          e05_str:=Wytnij(wiersz,4);
          e06_str:=Wytnij(wiersz,5);
          e07_str:=Wytnij(wiersz,6);
          e08_str:=Wytnij(wiersz,7);
          e09_str:=Wytnij(wiersz,8);
          e10_str:=Wytnij(wiersz,9);
          e11_str:=Wytnij(wiersz,10);
          e12_str:=Wytnij(wiersz,11);
          e13_str:=Wytnij(wiersz,12);
          if length(e01_str)>=5 then
            begin
              temp2_str:=copy(e01_str,1,4);
              temp3_str:=copy(e01_str,5,1);
              val(temp2_str,year,code);
              if ((code=0) and (temp3_str='.') and (e11_str=ADQ) and (y=year)) then
                begin
                  {Tabulators}
                  tabul:=FALSE;
                  for i:=1 to length(wiersz) do
                    begin
                      b:=ord(wiersz[i]);
                      if b=9 then
                        begin
                          tabul:=TRUE;
                        end;
                    end;
                  if tabul then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  The line contains a tabulator(s)');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {Position error}
                  a01_str:=Wytnij_sztywno(wiersz,0);
                  a02_str:=Wytnij_sztywno(wiersz,1);
                  a03_str:=Wytnij_sztywno(wiersz,2);
                  a04_str:=Wytnij_sztywno(wiersz,3);
                  a05_str:=Wytnij_sztywno(wiersz,4);
                  a06_str:=Wytnij_sztywno(wiersz,5);
                  a07_str:=Wytnij_sztywno(wiersz,6);
                  a08_str:=Wytnij_sztywno(wiersz,7);
                  a09_str:=Wytnij_sztywno(wiersz,8);
                  a10_str:=Wytnij_sztywno(wiersz,9);
                  a11_str:=Wytnij_sztywno(wiersz,10);
                  a12_str:=Wytnij_sztywno(wiersz,11);
                  a13_str:=Wytnij_sztywno(wiersz,12);
                  if not((e01_str=a01_str) and (e02_str=a02_str) and (e03_str=a03_str) and (e04_str=a04_str) and
                     (e05_str=a05_str) and (e06_str=a06_str) and (e07_str=a07_str) and (e08_str=a08_str) and
                     (e09_str=a09_str) and (e10_str=a10_str) and (e11_str=a11_str) and (e12_str=a12_str)) then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  Format shortcoming - suspected and expected line below');
                      writeln(fraport,'      "',wiersz,'"');
                      writeln(fraport,'      "',wzor_str,'"');
                    end;

                  {D_deg}
                  temp2_str:=Wytnij(wiersz,1);
                  val(temp2_str,D_deg,code);
                  if temp2_str='-0' then D_deg:=-0.0000000001;
                  if code<>0 then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Error D_deg or non-ASCII character');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {D_min}
                  temp2_str:=Wytnij(wiersz,2);
                  val(temp2_str,D_min,code);
                  if code<>0 then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Error D_min or non-ASCII character');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {I_deg}
                  temp2_str:=Wytnij(wiersz,3);
                  val(temp2_str,I_deg,code);
                  if temp2_str='-0' then I_deg:=-0.0000000001;
                  if code<>0 then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Error I_deg or non-ASCII character');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {I_min}
                  temp2_str:=Wytnij(wiersz,4);
                  val(temp2_str,I_min,code);
                  if code<>0 then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Error I_min or non-ASCII character');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {H_nT}
                  temp2_str:=Wytnij(wiersz,5);
                  val(temp2_str,H_nT,code);
                  if code<>0 then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Error H_nT or non-ASCII character');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {X_nT}
                  temp2_str:=Wytnij(wiersz,6);
                  val(temp2_str,X_nT,code);
                  if code<>0 then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Error X_nT or non-ASCII character');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {Y_nT}
                  temp2_str:=Wytnij(wiersz,7);
                  val(temp2_str,Y_nT,code);
                  if code<>0 then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Error Y_nT or non-ASCII character');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {Z_nT}
                  temp2_str:=Wytnij(wiersz,8);
                  val(temp2_str,Z_nT,code);
                  if code<>0 then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Error Z_nT or non-ASCII character');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {F_nT}
                  temp2_str:=Wytnij(wiersz,9);
                  val(temp2_str,F_nT,code);
                  if code<>0 then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Error F_nT or non-ASCII character');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {Fobl-F_nT}
                  Fobl:=sqrt(X_nT*X_nT+Y_nT*Y_nT+Z_nT*Z_nT);
                  Fdelta:=Fobl-F_nT;
                  Fdelta:=Fdelta;
                  if ((Abs(Fdelta)>=2.0) and (X_nT<99999) and (Y_nT<99999) and (Z_nT<99999) and (F_nT<99999)) then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Discrepancy sqrt(XX+YY+ZZ)-F=',Fdelta:3:1,'nT');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {Hobl-H_nT}
                  Hobl:=sqrt(X_nT*X_nT+Y_nT*Y_nT);
                  Hdelta:=Hobl-H_nT;
                  Hdelta:=Hdelta;
                  if ((Abs(Hdelta)>=2.0) and (X_nT<99999) and (Y_nT<99999) and (H_nT<99999)) then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Discrepancy sqrt(XX+YY)-H=',Hdelta:3:1,'nT');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {H*sin(D) - Y}
                  if D_deg>=0.0 then
                    Yobl:=H_nT*sin((D_deg+D_min/60)*pi/180.0)
                  else
                    Yobl:=H_nT*sin((D_deg-D_min/60)*pi/180.0);
                  Ydelta:=Yobl-Y_nT;
                  if ((Abs(Ydelta)>=2.0) and (Abs(D_deg)<999) and (Abs(D_min)<99.9) and (H_nT<99999)) then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Discrepancy H*sin(D)-Y=',Ydelta:3:1,'nT');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                  {F*cos(I) = H}
                  if I_deg>=0.0 then
                    Hobl1:=F_nT*cos((I_deg+I_min/60)*pi/180.0)
                  else
                    Hobl1:=F_nT*cos((I_deg-I_min/60)*pi/180.0);
                  Hdelta:=Hobl1-H_nT;
                  if ((Abs(Hdelta)>=2.0) and (Abs(I_deg)<999) and (Abs(I_min)<99.9) and (H_nT<99999) and (F_nT<99999)) then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Discrepancy F*cos(I)-H=',Hdelta:3:1,'nT');
                      writeln(fraport,'      "',wiersz,'"');
                    end;


                  {F*sin(I) = Z}
                  if I_deg>=0.0 then
                    Zobl1:=F_nT*sin((I_deg+I_min/60)*pi/180.0)
                  else
                    Zobl1:=F_nT*sin((I_deg-I_min/60)*pi/180.0);
                  Zdelta:=Zobl1-Z_nT;
                  if ((Abs(Zdelta)>=2.0) and (Abs(I_deg)<999) and (Abs(I_min)<99.9) and (Z_nT<99999) and (F_nT<99999)) then
                    begin
                      err:=err+1;
                      writeln(fraport,'   !  ',y,'   Discrepancy F*sin(I)-Z=',Zdelta:3:1,'nT');
                      writeln(fraport,'      "',wiersz,'"');
                    end;

                end;
            end;
        end; {while not eof(fyear)}
      close(fyear);
    end; {for y:=year_min to year_max do}
end; {Procedure Discrepancy}


Procedure Wyswietl_Raport;
{ENG. Reads report file and displays on the screen, this procedure is not used finally}
var temp1_str:string250;
begin {Procedure Wyswietl_Raport}
  reset(fraport);
  while not eof(fraport) do
    begin
      readln(fraport,temp1_str);
      writeln(temp1_str);
    end;
  CloseFile(fraport);
end; {Procedure Wyswietl_Raport}



begin {procedure ymchk}

    begin {dobra ilosc parametrow}

                 begin {jest YEARMEAN.COD}

                   if yearmean_EOL=1 then
                     begin
                       file_yearmean_str:=Dir_iaf_str+'\YEARMEAN.'+IMO_str;
                     end
                   else
                     begin
                       Text_Any_System_to_Windows(Dir_iaf_str+'\YEARMEAN.'+IMO_str,'tmp_check1min.tmp');
                       file_yearmean_str:='tmp_check1min.tmp';
                     end;

                   {HEADER LINES ERRORS}
                   writeln(fraport,'HEADER LINES errors:');
                   writeln(fraport,'   header not inspected');

                   Check_LineLengths;

                   Find_Min_All;
                   Find_Max_All;
                   writeln(fraport,'ALL DAYS data:');
                   if ((year_min=2035) and (year_max=1850)) then
                     begin
                       writeln(fraport,'   ! No ALL DAYS data')
                     end
                   else
                     begin
                       if ((year_min>1850) and (year_min<2035) and (year_max>1850) and (year_max<2035)
                       and (year_max>=year_min)) then
                         begin
                           writeln(fraport,'   Start: ',year_min);
                           writeln(fraport,'   End:   ',year_max);
                           Find_Missing_All;
                           writeln(fraport,'   Discrepancies or format errors:');
                           err:=0;
                           Discrepancy('A');
                           if err=0 then
                             writeln(fraport,'      OK');
                           {
                           writeln(fraport,'   ALL DAYS - DISCREPANCIES WITH BINARY DATA:');
                           writeln(fraport,'      ! NOT inspected - please check manually');
                           }
                         end
                       else
                         begin
                           writeln(fraport,'   ! the OLDEST or the YOUNGEST year is not realistic');
                         end;
                     end;

                   Find_Min_Quiet;
                   Find_Max_Quiet;
                   writeln(fraport,'QUIET DAYS data:');
                   if ((year_min=2035) and (year_max=1850)) then
                     begin
                       writeln(fraport,'   ! No QUIET DAYS data')
                     end
                   else
                     begin
                       if ((year_min>1850) and (year_min<2035) and (year_max>1850) and (year_max<2035)
                       and (year_max>=year_min)) then
                         begin
                           writeln(fraport,'   Start: ',year_min);
                           writeln(fraport,'   End:   ',year_max);
                           Find_Missing_Quiet;
                           writeln(fraport,'   Discrepancies or format errors:');
                           err:=0;
                           Discrepancy('Q');
                           if err=0 then
                             writeln(fraport,'      OK');
                         end
                       else
                         begin
                           writeln(fraport,'   ! the OLDEST or the YOUNGEST year is not realistic');
                         end;
                     end;


                   Find_Min_Disturbed;
                   Find_Max_Disturbed;
                   writeln(fraport,'DISTURBED DAYS data:');
                   if ((year_min=2035) and (year_max=1850)) then
                     begin
                       writeln(fraport,'   ! No DISTURBED DAYS data')
                     end
                   else
                     begin
                       if ((year_min>1850) and (year_min<2035) and (year_max>1850) and (year_max<2035)
                       and (year_max>=year_min)) then
                         begin
                           writeln(fraport,'   Start: ',year_min);
                           writeln(fraport,'   End:   ',year_max);
                           Find_Missing_Disturbed;
                           writeln(fraport,'   Disrepancies or format errors:');
                           err:=0;
                           Discrepancy('D');
                           if err=0 then
                             writeln(fraport,'      OK');
                         end
                       else
                         begin
                           writeln(fraport,'   ! the OLDEST or the YOUNGEST year is not realistic');
                         end;
                     end;

                   Find_Min_Incomplete;
                   Find_Max_Incomplete;
                   writeln(fraport,'INCOMPLETE DAYS data:');
                   if ((year_min=2035) and (year_max=1850)) then
                     begin
                       writeln(fraport,'   ! No INCOMPLETE DAYS data')
                     end
                   else
                     begin
                       if ((year_min>1850) and (year_min<2035) and (year_max>1850) and (year_max<2035)
                       and (year_max>=year_min)) then
                         begin
                           writeln(fraport,'   Start: ',year_min);
                           writeln(fraport,'   End:   ',year_max);
                           writeln(fraport,'   Discrepancies or format errors:');
                           err:=0;
                           Discrepancy('I');
                           if err=0 then
                             writeln(fraport,'      OK');
                         end
                       else
                         begin
                           writeln(fraport,'   ! the OLDEST or the YOUNGEST year is not realistic');
                         end;
                     end;

                   writeln(fraport);
                   writeln(fraport);
                 end; {jest YEARMEAN.COD}




    end; {dobra ilosc parametrow}
    if yearmean_EOL<>1 then
      begin
        DeleteFile('tmp_check1min.tmp');
      end;
  end;{procedure ymchk}

{======================================================================================}




Procedure Text_Any_System_to_Windows(File1_str:string250; File2_str:string250);
var fil1,fil2:text;
    f1_str,f2_str:string250;
    line1,line2:string;
begin {Procedure Text_Any_System_to_Windows}
  f1_str:=ExpandFileName(File1_str);
  f2_str:=ExpandFileName(File2_str);
  AssignFile(fil1,f1_str);
  AssignFile(fil2,f2_str);
  reset(fil1);
  rewrite(fil2);
  while not eof(fil1) do
    begin
      readln(fil1,line1);
      line2:=AdjustLineBreaks(line1);
      writeln(fil2,line2);
    end;
  CloseFile(fil1);
  CloseFile(fil2);
end; {Procedure Text_Any_System_to_Windows}


Function Detect_system_EOL(Fil_text_str:string250):integer;
{==============================================
|   0 - nie okreslono                         |
|   1 - CrLf   Windows/DOS                    |
|   2 - Cr     Macintosh                      |
|   3 - Lf     Linux/Unix                     |
==============================================}
var fil:file of char;
    fstr:string250;
    fileContent: string;
    c: char;
    Len,n:integer;
    i:integer;
    found_eol:boolean;
begin {Detect_system_EOL}
  Detect_system_EOL:=0;
  fstr:=ExpandFileName(Fil_text_str);
  AssignFile(fil,fstr);
  reset(fil);
  Len := FileSize(fil);
  n:=Len;
  while n > 0 do
    begin
      Read(fil, c);
      fileContent := fileContent + c;
      dec(n);
    end;
  CloseFile(fil);
  i:=2;
  found_eol:=FALSE;
  repeat
    c:=fileContent[i];
    if ((ord(c)=10) or (ord(c)=13)) then
      found_eol:=TRUE;
    i:=i+1;
  until ((i>Len) or (found_eol));
  i:=i-1;
  if found_eol then
    begin {if found_eol then}
    
      if ord(fileContent[i])=10 then
        begin {Lf}
          if ord(fileContent[i-1])=13 then
            begin {poprzedni=13}
              Detect_system_EOL:=1; {Windows}
            end; {poprzedni=13}
          if ord(fileContent[i-1])<>13 then
            begin {poprzedni<>13}
              Detect_system_EOL:=3; {Unix/Linux}
            end; {poprzedni<>13}
        end; {Lf}

      if ord(fileContent[i])=13 then
        begin {Cr}
          if ord(fileContent[i+1])=10 then
            begin {nastepny=10}
              Detect_system_EOL:=1; {Windows}
            end; {nastepny=10}
          if ord(fileContent[i+1])<>10 then
            begin {nastepny<>10}
              Detect_system_EOL:=2; {Macintosh}
            end; {nastepny<>10}
        end; {Cr}

    end; {if found_eol then}

end; {Detect_system_EOL}


Procedure Czy_sa_IAF;
{Czy_sa_IAF means Are there IAF files}
var i,l:integer;
    temp1_str:string250;
    f_size:integer;
    fil:file of byte;
begin {Procedure Czy_sa_IAF}
  l:=0;
  IAF_present:=FALSE;
  for i:=1 to 12 do
    begin
      temp1_str:=dir_iaf_str+'\'+IMO_str+copy(year_str,3,2)+monthnames[i]+'.bin';
      if Exist_File(temp1_str) then
        begin
          AssignFile(fil,temp1_str);
          Reset(fil);
          f_size:=FileSize(fil);
          CloseFile(fil);
          if ((i=1) or (i=3) or (i=5) or (i=7) or (i=8) or (i=10) or (i=12)) and (f_size=730112) then
            begin
              l:=l+1;
            end;
          if ((i=4) or (i=6) or (i=9) or (i=11)) and (f_size=706560) then
            begin
              l:=l+1;
            end;
          if ((i=2) and (frac(year/4)=0.0) and (f_size=683008)) then
            begin
              l:=l+1;
            end;
          if ((i=2) and (frac(year/4)<>0.0) and (f_size=659456)) then
            begin
              l:=l+1;
            end;
        end;
    end;
    if l<>12 then
      begin
        writeln;
        writeln('WARNING: There is not complete 12 IAF files ',dir_iaf_str+'\'+IMO_str+copy(year_str,3,2)+'???.bin',' or size(s) is not correct - please check');
        writeln(fraport,'WARNING: There is not ',dir_iaf_str+'\'+IMO_str+copy(year_str,3,2)+'???.bin','  (not all files or wrong name or wrong length and so on)');
        writeln(fraport);
        CloseFile(fraport);
        {
        writeln(' Press ESC');
        repeat
          ch_esc:=ReadKey;
        until ch_esc=#27;
        }
        halt;
      end
    else
      begin
        IAF_present:=TRUE;
      end;
end; {Procedure Czy_sa_IAF}

Procedure Czy_jest_yearmean;
{Is there yearmean file?}
var temp1_str:string250;
begin {Procedure Czy_jest_yearmean}
  yearmean_file_present:=FALSE;
  temp1_str:=dir_iaf_str+'\yearmean.'+IMO_str;
  if Exist_File(temp1_str) then
    begin
      yearmean_file_present:=TRUE;
    end
  else
    begin
      writeln;
      writeln(fraport,'WARNING: Missing ',dir_iaf_str+'\'+'yearmean.',IMO_str);
      writeln('WARNING: Missing ',dir_iaf_str+'\'+'yearmean.',IMO_str);

      {
      writeln(' Press ESC');
      repeat
        ch_esc:=ReadKey;
      until ch_esc=#27;
      }
    end;
end; {Procedure Czy_jest_yearmean}

Procedure Czy_jest_BLV;
{Is there BLV file?}
var temp1_str:string250;
begin {Procedure Czy_jest_BLV}
  BLV_present:=FALSE;
  temp1_str:=dir_iaf_str+'\'+IMO_str+year_str+'.blv';
  if Exist_File(temp1_str) then
    begin
      BLV_present:=TRUE;
    end
  else
    begin
      writeln;
      writeln(fraport,'WARNING: Missing ',dir_iaf_str+'\'+IMO_str+year_str+'.blv');
      writeln('WARNING: Missing ',dir_iaf_str+'\'+IMO_str+year_str+'.blv');
      {
      writeln(' Press ESC');
      repeat
        ch_esc:=ReadKey;
      until ch_esc=#27;
      }
    end;
end; {Procedure Czy_jest_BLV}

Procedure Czy_jest_ReadmeIMO;
var temp1_str:string250;
begin {Procedure Czy_jest_ReadmeIMO}
  ReadmeIMO_present:=FALSE;
  temp1_str:=dir_iaf_str+'\readme.'+IMO_str;
  if Exist_File(temp1_str) then
    begin
      ReadmeIMO_present:=TRUE;
    end
  else
    begin
      writeln;
      writeln(fraport,'WARNING: Missing ',dir_iaf_str+'\'+'readme.'+IMO_str);
      writeln('WARNING: Missing ',dir_iaf_str+'\'+'readme.'+IMO_str);
      {
      writeln(' Press ESC');
      repeat
        ch_esc:=ReadKey;
      until ch_esc=#27;
      }
    end;
end; {Procedure Czy_jest_ReadmeIMO}


Procedure Read_IAF_headers;
var m,d,w:integer;
    fil_str:string250;
    fi:file;
    buf:array[1..800000] of byte;
    result:integer;
    il_dni:integer;
    doy:integer;
    Max_doy:integer;
    Headers_byte: array [1..366,1..64] of byte;
begin {Procedure Read_IAF_headers}
  doy:=1;
  for m:=1 to 12 do
    begin {for m:=1 to 12 do}
      fil_str:=dir_iaf_str+'\'+IMO_str+copy(year_str,3,2)+monthnames[m]+'.bin';
      assign(fi,fil_str);
      reset(fi,1);
      BlockRead(fi,buf,800000,result);
      close(fi);
      il_dni:=result div (5888*4);
      for d:=1 to il_dni do
        begin {for d:=1 to il_dni do}
          for w:=1 to 16 do
            begin
              Headers_byte[doy,(w-1)*4+1]:=buf[(d-1)*4*5888+(w-1)*4+1];
              Headers_byte[doy,(w-1)*4+2]:=buf[(d-1)*4*5888+(w-1)*4+2];
              Headers_byte[doy,(w-1)*4+3]:=buf[(d-1)*4*5888+(w-1)*4+3];
              Headers_byte[doy,(w-1)*4+4]:=buf[(d-1)*4*5888+(w-1)*4+4];
            end;
          doy:=doy+1;
        end; {for d:=1 to il_dni do}
      Max_doy:=doy-1;
    end; {for m:=1 to 12 do}
  for d:=1 to Max_doy do
    begin {for d:=1 to Max_doy do}
      Headers[d].W01:= chr(Headers_byte[d,0*4+1])
                      +chr(Headers_byte[d,0*4+2])
                      +chr(Headers_byte[d,0*4+3])
                      +chr(Headers_byte[d,0*4+4]);
      Headers[d].W02:= 1*           Headers_byte[d,1*4+1]
                       +256*        Headers_byte[d,1*4+2]
                       +256*256*    Headers_byte[d,1*4+3]
                       +256*256*256*Headers_byte[d,1*4+4];
      Headers[d].W03:= 1*           Headers_byte[d,2*4+1]
                       +256*        Headers_byte[d,2*4+2]
                       +256*256*    Headers_byte[d,2*4+3]
                       +256*256*256*Headers_byte[d,2*4+4];
      Headers[d].W04:= 1*           Headers_byte[d,3*4+1]
                       +256*        Headers_byte[d,3*4+2]
                       +256*256*    Headers_byte[d,3*4+3]
                       +256*256*256*Headers_byte[d,3*4+4];
      Headers[d].W05:= 1*           Headers_byte[d,4*4+1]
                       +256*        Headers_byte[d,4*4+2]
                       +256*256*    Headers_byte[d,4*4+3]
                       +256*256*256*Headers_byte[d,4*4+4];
      Headers[d].W06:= chr(Headers_byte[d,5*4+1])
                      +chr(Headers_byte[d,5*4+2])
                      +chr(Headers_byte[d,5*4+3])
                      +chr(Headers_byte[d,5*4+4]);
      Headers[d].W07:= chr(Headers_byte[d,6*4+1])
                      +chr(Headers_byte[d,6*4+2])
                      +chr(Headers_byte[d,6*4+3])
                      +chr(Headers_byte[d,6*4+4]);
      Headers[d].W08:= 1*           Headers_byte[d,7*4+1]
                       +256*        Headers_byte[d,7*4+2]
                       +256*256*    Headers_byte[d,7*4+3]
                       +256*256*256*Headers_byte[d,7*4+4];
      Headers[d].W09:= chr(Headers_byte[d,8*4+1])
                      +chr(Headers_byte[d,8*4+2])
                      +chr(Headers_byte[d,8*4+3])
                      +chr(Headers_byte[d,8*4+4]);
      Headers[d].W10:= chr(Headers_byte[d,9*4+1])
                      +chr(Headers_byte[d,9*4+2])
                      +chr(Headers_byte[d,9*4+3])
                      +chr(Headers_byte[d,9*4+4]);
      Headers[d].W11:= 1*           Headers_byte[d,10*4+1]
                       +256*        Headers_byte[d,10*4+2]
                       +256*256*    Headers_byte[d,10*4+3]
                       +256*256*256*Headers_byte[d,10*4+4];
      Headers[d].W12:= 1*           Headers_byte[d,11*4+1]
                       +256*        Headers_byte[d,11*4+2]
                       +256*256*    Headers_byte[d,11*4+3]
                       +256*256*256*Headers_byte[d,11*4+4];
      Headers[d].W13:= chr(Headers_byte[d,12*4+1])
                      +chr(Headers_byte[d,12*4+2])
                      +chr(Headers_byte[d,12*4+3])
                      +chr(Headers_byte[d,12*4+4]);
      Headers[d].W14:= chr(Headers_byte[d,13*4+1])
                      +chr(Headers_byte[d,13*4+2])
                      +chr(Headers_byte[d,13*4+3])
                      +chr(Headers_byte[d,13*4+4]);
      Headers[d].W15:= 1*           Headers_byte[d,14*4+1]
                       +256*        Headers_byte[d,14*4+2]
                       +256*256*    Headers_byte[d,14*4+3]
                       +256*256*256*Headers_byte[d,14*4+4];
      Headers[d].W16:= 1*           Headers_byte[d,15*4+1]
                       +256*        Headers_byte[d,15*4+2]
                       +256*256*    Headers_byte[d,15*4+3]
                       +256*256*256*Headers_byte[d,15*4+4];
    end; {for d:=1 to Max_doy do}
end; {Procedure Read_IAF_headers}


Procedure Read_XYZG_minute;
var m,d,min:integer;
    fil_str:string250;
    fi:file;
    buf:array[1..800000] of byte;
    result:integer;
    il_dni:integer;
    moy:integer; {minuta roku licac od 0}
begin {Procedure Read_XYZG_minute}
  moy:=0;
  for m:=1 to 12 do
    begin {for m:=1 to 12 do}
      fil_str:=dir_iaf_str+'\'+IMO_str+copy(year_str,3,2)+monthnames[m]+'.bin';
      assign(fi,fil_str);
      reset(fi,1);
      BlockRead(fi,buf,800000,result);
      close(fi);
      il_dni:=result div (5888*4);
      for d:=1 to il_dni do
        begin {for d:=1 to il_dni do}
          for min:=0 to 1439 do
            begin {for min:=0 to 1439 do}
              XYZG_minute[moy,1]:=1*           buf[5888*4*(d-1)+16*4+0*1440*4+min*4+1]
                                  +256*        buf[5888*4*(d-1)+16*4+0*1440*4+min*4+2]
                                  +256*256*    buf[5888*4*(d-1)+16*4+0*1440*4+min*4+3]
                                  +256*256*256*buf[5888*4*(d-1)+16*4+0*1440*4+min*4+4];
              XYZG_minute[moy,2]:=1*           buf[5888*4*(d-1)+16*4+1*1440*4+min*4+1]
                                  +256*        buf[5888*4*(d-1)+16*4+1*1440*4+min*4+2]
                                  +256*256*    buf[5888*4*(d-1)+16*4+1*1440*4+min*4+3]
                                  +256*256*256*buf[5888*4*(d-1)+16*4+1*1440*4+min*4+4];
              XYZG_minute[moy,3]:=1*           buf[5888*4*(d-1)+16*4+2*1440*4+min*4+1]
                                  +256*        buf[5888*4*(d-1)+16*4+2*1440*4+min*4+2]
                                  +256*256*    buf[5888*4*(d-1)+16*4+2*1440*4+min*4+3]
                                  +256*256*256*buf[5888*4*(d-1)+16*4+2*1440*4+min*4+4];
              XYZG_minute[moy,4]:=1*           buf[5888*4*(d-1)+16*4+3*1440*4+min*4+1]
                                  +256*        buf[5888*4*(d-1)+16*4+3*1440*4+min*4+2]
                                  +256*256*    buf[5888*4*(d-1)+16*4+3*1440*4+min*4+3]
                                  +256*256*256*buf[5888*4*(d-1)+16*4+3*1440*4+min*4+4];
              moy:=moy+1;
            end; {for min:=1 to 1440 do}
        end; {for d:=1 to il_dni do}
    end; {for m:=1 to 12 do}
end; {Procedure Read_XYZG_minute}


Procedure Read_XYZG_hour;
var m,d,h:integer;
    fil_str:string250;
    fi:file;
    buf:array[1..800000] of byte;
    result:integer;
    il_dni:integer;
    hoy:integer; {godzina roku liczac od 0}
begin {Procedure Read_XYZG_hour}
  hoy:=0;
  for m:=1 to 12 do
    begin {for m:=1 to 12 do}
      fil_str:=dir_iaf_str+'\'+IMO_str+copy(year_str,3,2)+monthnames[m]+'.bin';
      assign(fi,fil_str);
      reset(fi,1);
      BlockRead(fi,buf,800000,result);
      close(fi);
      il_dni:=result div (5888*4);
      for d:=1 to il_dni do
        begin {for d:=1 to il_dni do}
          for h:=0 to 23 do
            begin {for h:=0 to 23 do}
              XYZG_hour[hoy,1]:=1*           buf[5888*4*(d-1)+5776*4+h*4+0*96+1]
                                +256*        buf[5888*4*(d-1)+5776*4+h*4+0*96+2]
                                +256*256*    buf[5888*4*(d-1)+5776*4+h*4+0*96+3]
                                +256*256*256*buf[5888*4*(d-1)+5776*4+h*4+0*96+4];
              XYZG_hour[hoy,2]:=1*           buf[5888*4*(d-1)+5776*4+h*4+1*96+1]
                                +256*        buf[5888*4*(d-1)+5776*4+h*4+1*96+2]
                                +256*256*    buf[5888*4*(d-1)+5776*4+h*4+1*96+3]
                                +256*256*256*buf[5888*4*(d-1)+5776*4+h*4+1*96+4];
              XYZG_hour[hoy,3]:=1*           buf[5888*4*(d-1)+5776*4+h*4+2*96+1]
                                +256*        buf[5888*4*(d-1)+5776*4+h*4+2*96+2]
                                +256*256*    buf[5888*4*(d-1)+5776*4+h*4+2*96+3]
                                +256*256*256*buf[5888*4*(d-1)+5776*4+h*4+2*96+4];
              XYZG_hour[hoy,4]:=1*           buf[5888*4*(d-1)+5776*4+h*4+3*96+1]
                                +256*        buf[5888*4*(d-1)+5776*4+h*4+3*96+2]
                                +256*256*    buf[5888*4*(d-1)+5776*4+h*4+3*96+3]
                                +256*256*256*buf[5888*4*(d-1)+5776*4+h*4+3*96+4];
              hoy:=hoy+1;
            end; {for h:=0 to 23 do}
        end; {for d:=1 to il_dni do}
    end; {for m:=1 to 12 do}
end; {Procedure Read_XYZG_hour}


Procedure Read_XYZG_day;
var m,d:integer;
    fil_str:string250;
    fi:file;
    buf:array[1..800000] of byte;
    result:integer;
    il_dni:integer;
    doy:integer; {dzien roku liczac od 1}
begin {Procedure Read_XYZG_day}
  doy:=1;
  for m:=1 to 12 do
    begin {for m:=1 to 12 do}
      fil_str:=dir_iaf_str+'\'+IMO_str+copy(year_str,3,2)+monthnames[m]+'.bin';
      assign(fi,fil_str);
      reset(fi,1);
      BlockRead(fi,buf,800000,result);
      close(fi);
      il_dni:=result div (5888*4);
      for d:=1 to il_dni do
        begin {for d:=1 to il_dni do}
          XYZG_day[doy,1]:=1*           buf[5888*4*(d-1)+5872*4+1]
                           +256*        buf[5888*4*(d-1)+5872*4+2]
                           +256*256*    buf[5888*4*(d-1)+5872*4+3]
                           +256*256*256*buf[5888*4*(d-1)+5872*4+4];
          XYZG_day[doy,2]:=1*           buf[5888*4*(d-1)+5872*4+5]
                           +256*        buf[5888*4*(d-1)+5872*4+6]
                           +256*256*    buf[5888*4*(d-1)+5872*4+7]
                           +256*256*256*buf[5888*4*(d-1)+5872*4+8];
          XYZG_day[doy,3]:=1*           buf[5888*4*(d-1)+5872*4+9]
                           +256*        buf[5888*4*(d-1)+5872*4+10]
                           +256*256*    buf[5888*4*(d-1)+5872*4+11]
                           +256*256*256*buf[5888*4*(d-1)+5872*4+12];
          XYZG_day[doy,4]:=1*           buf[5888*4*(d-1)+5872*4+13]
                           +256*        buf[5888*4*(d-1)+5872*4+14]
                           +256*256*    buf[5888*4*(d-1)+5872*4+15]
                           +256*256*256*buf[5888*4*(d-1)+5872*4+16];
          doy:=doy+1;
        end; {for d:=1 to il_dni do}
    end; {for m:=1 to 12 do}
end; {Procedure Read_XYZG_day}


Procedure Read_Kindices;
var m,d:integer;
    fil_str:string250;
    fi:file;
    buf:array[1..800000] of byte;
    result:integer;
    il_dni:integer;
    doy:integer; {dzien roku liczac od 1}
begin {Procedure Read_Kindices}
  doy:=1;
  for m:=1 to 12 do
    begin {for m:=1 to 12 do}
      fil_str:=dir_iaf_str+'\'+IMO_str+copy(year_str,3,2)+monthnames[m]+'.bin';
      assign(fi,fil_str);
      reset(fi,1);
      BlockRead(fi,buf,800000,result);
      close(fi);
      il_dni:=result div (5888*4);
      for d:=1 to il_dni do
        begin {for d:=1 to il_dni do}
          Indices[doy,1]:=1*           buf[5888*4*(d-1)+5876*4+1]
                          +256*        buf[5888*4*(d-1)+5876*4+2]
                          +256*256*    buf[5888*4*(d-1)+5876*4+3]
                          +256*256*256*buf[5888*4*(d-1)+5876*4+4];
          Indices[doy,2]:=1*           buf[5888*4*(d-1)+5876*4+5]
                          +256*        buf[5888*4*(d-1)+5876*4+6]
                          +256*256*    buf[5888*4*(d-1)+5876*4+7]
                          +256*256*256*buf[5888*4*(d-1)+5876*4+8];
          Indices[doy,3]:=1*           buf[5888*4*(d-1)+5876*4+9]
                          +256*        buf[5888*4*(d-1)+5876*4+10]
                          +256*256*    buf[5888*4*(d-1)+5876*4+11]
                          +256*256*256*buf[5888*4*(d-1)+5876*4+12];
          Indices[doy,4]:=1*           buf[5888*4*(d-1)+5876*4+13]
                          +256*        buf[5888*4*(d-1)+5876*4+14]
                          +256*256*    buf[5888*4*(d-1)+5876*4+15]
                          +256*256*256*buf[5888*4*(d-1)+5876*4+16];
          Indices[doy,5]:=1*           buf[5888*4*(d-1)+5876*4+17]
                          +256*        buf[5888*4*(d-1)+5876*4+18]
                          +256*256*    buf[5888*4*(d-1)+5876*4+19]
                          +256*256*256*buf[5888*4*(d-1)+5876*4+20];
          Indices[doy,6]:=1*           buf[5888*4*(d-1)+5876*4+21]
                          +256*        buf[5888*4*(d-1)+5876*4+22]
                          +256*256*    buf[5888*4*(d-1)+5876*4+23]
                          +256*256*256*buf[5888*4*(d-1)+5876*4+24];
          Indices[doy,7]:=1*           buf[5888*4*(d-1)+5876*4+25]
                          +256*        buf[5888*4*(d-1)+5876*4+26]
                          +256*256*    buf[5888*4*(d-1)+5876*4+27]
                          +256*256*256*buf[5888*4*(d-1)+5876*4+28];
          Indices[doy,8]:=1*           buf[5888*4*(d-1)+5876*4+29]
                          +256*        buf[5888*4*(d-1)+5876*4+30]
                          +256*256*    buf[5888*4*(d-1)+5876*4+31]
                          +256*256*256*buf[5888*4*(d-1)+5876*4+32];
          doy:=doy+1;
        end; {for d:=1 to il_dni do}
    end; {for m:=1 to 12 do}
end; {Procedure Read_Kindices}


Procedure Check_Headers;

Procedure Check_W01;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W01}
  line_str:='';
  line_str:=line_str+'W01 Station code             '+' "'+Headers[1].W01+'"  (';
  temp1_str:=IntToHex(ord(Headers[1].W01[1]),2)+' '+
             IntToHex(ord(Headers[1].W01[2]),2)+' '+
             IntToHex(ord(Headers[1].W01[3]),2)+' '+
             IntToHex(ord(Headers[1].W01[4]),2);
  line_str:=line_str+temp1_str+') ';
  if Test_Spacje_OK(Headers[1].W01) then
    begin {Spacje OK}
      il_problemow:=0;
      doy:=2;
      repeat
        if  Headers[doy].W01<>Headers[1].W01 then
          begin
            il_problemow:=il_problemow+1;
            line_str:=line_str+'unexpected change    W01='+Headers[doy].W01+'    day_of_year='+Leading_Zero(doy,3);
          end;
        doy:=doy+1;
      until ((doy=Max_day+1) or (il_problemow>0));
    end {Spacje OK}
  else
    begin {Spacje not OK}
      line_str:=line_str+'3-letter code should preceded by a space (http://www.intermagnet.org/data-donnee/formats/iaf-eng.php)';
    end; {Spacje not OK}
  writeln(fraport,line_str);
end; {Procedure Check_W01}

Procedure Check_W02;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W02}
  line_str:='';
  line_str:=line_str+'W02 Year and day number      '+Leading_Space(Headers[1].W02,7)+'  (';
  temp1_str:=IntToHex(Headers[1].W02,8);
  temp1_str:=Rewer_Hex(temp1_str);
  Insert(' ', temp1_str, 3);
  Insert(' ', temp1_str, 6);
  Insert(' ', temp1_str, 9);
  line_str:=line_str+temp1_str+') ';
  il_problemow:=0;
  doy:=2;
  repeat
    if  (Headers[doy].W02-Headers[doy-1].W02<>1) then
      begin
        il_problemow:=il_problemow+1;
        line_str:=line_str+'Expected_doy='+Leading_Zero(Headers[doy-1].W02+1,8)+' Reported_doy='+Leading_Zero(Headers[doy].W02,8);
      end;
    doy:=doy+1;
  until ((doy=Max_day+1) or (il_problemow>0));
  writeln(fraport,line_str);
end; {Procedure Check_W02}


Procedure Check_W03;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W03}
  line_str:='';
  line_str:=line_str+'W03 Co-latitude (deg x 1000) '+Leading_Space(Headers[1].W03,7)+'  (';
  temp1_str:=IntToHex(Headers[1].W03,8);
  temp1_str:=Rewer_Hex(temp1_str);
  Insert(' ', temp1_str, 3);
  Insert(' ', temp1_str, 6);
  Insert(' ', temp1_str, 9);
  line_str:=line_str+temp1_str+') ';
  il_problemow:=0;
  doy:=2;
  repeat
    if  (Headers[doy].W03<>Headers[1].W03) then
      begin
        il_problemow:=il_problemow+1;
        line_str:=line_str+'unexpected change    W03='+Leading_Space(Headers[doy].W03,7)+'    day_of_year='+Leading_Zero(doy,3);
      end;
    doy:=doy+1;
  until ((doy=Max_day+1) or (il_problemow>0));
  writeln(fraport,line_str);
end; {Procedure Check_W03}


Procedure Check_W04;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W04}
  line_str:='';
  line_str:=line_str+'W04 Longitude (deg x 1000)   '+Leading_Space(Headers[1].W04,7)+'  (';
  temp1_str:=IntToHex(Headers[1].W04,8);
  temp1_str:=Rewer_Hex(temp1_str);
  Insert(' ', temp1_str, 3);
  Insert(' ', temp1_str, 6);
  Insert(' ', temp1_str, 9);
  line_str:=line_str+temp1_str+') ';
  il_problemow:=0;
  doy:=2;
  repeat
    if  (Headers[doy].W04<>Headers[1].W04) then
      begin
        il_problemow:=il_problemow+1;
        line_str:=line_str+'unexpected change    W04='+Leading_Space(Headers[doy].W04,7)+'    day_of_year='+Leading_Zero(doy,3);
      end;
    doy:=doy+1;
  until ((doy=Max_day+1) or (il_problemow>0));
  writeln(fraport,line_str);
end; {Procedure Check_W04}


Procedure Check_W05;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W05}
  line_str:='';
  line_str:=line_str+'W05 Elevation (metres)       '+Leading_Space(Headers[1].W05,7)+'  (';
  temp1_str:=IntToHex(Headers[1].W05,8);
  temp1_str:=Rewer_Hex(temp1_str);
  Insert(' ', temp1_str, 3);
  Insert(' ', temp1_str, 6);
  Insert(' ', temp1_str, 9);
  line_str:=line_str+temp1_str+') ';
  il_problemow:=0;
  doy:=2;
  repeat
    if  (Headers[doy].W05<>Headers[1].W05) then
      begin
        il_problemow:=il_problemow+1;
        line_str:=line_str+'unexpected change    W05='+Leading_Space(Headers[doy].W05,7)+'    day_of_year='+Leading_Zero(doy,3);
      end;
    doy:=doy+1;
  until ((doy=Max_day+1) or (il_problemow>0));
  writeln(fraport,line_str);
end; {Procedure Check_W05}


Procedure Check_W06;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W06}
  line_str:='';
  line_str:=line_str+'W06 Reported elements        '+' "'+Headers[1].W06+'"  (';
  temp1_str:=IntToHex(ord(Headers[1].W06[1]),2)+' '+
             IntToHex(ord(Headers[1].W06[2]),2)+' '+
             IntToHex(ord(Headers[1].W06[3]),2)+' '+
             IntToHex(ord(Headers[1].W06[4]),2);
  line_str:=line_str+temp1_str+') ';
  if Test_Spacje_OK(Headers[1].W06) then
    begin {Spacje OK}
      il_problemow:=0;
      doy:=2;
      repeat
        if  Headers[doy].W06<>Headers[1].W06 then
          begin
            il_problemow:=il_problemow+1;
            line_str:=line_str+'unexpected change    W06='+Headers[doy].W06+'    day_of_year='+Leading_Zero(doy,3);
          end;
        doy:=doy+1;
      until ((doy=Max_day+1) or (il_problemow>0));
      writeln(fraport,line_str);
    end {Spacje OK}
  else
    begin {Spacje not OK}
      line_str:=line_str+'A string shorter than 4 chars should be padded to the left with spaces (http://www.intermagnet.org/data-donnee/formats/iaf-eng.php)';
      writeln(fraport,line_str);
    end; {Spacje not OK}
  if ((Trim(Headers[1].W06)='XYZ') or
      (Headers[1].W06='XYZG')) then
    begin
      {nic nie rob}
    end
  else
    begin
      line_str:='                              INTERMAGNET suggests to use a reported elements XYZG or XYZ';
      writeln(fraport,line_str);
    end;
end; {Procedure Check_W06}


Procedure Check_W07;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W07}
  line_str:='';
  line_str:=line_str+'W07 Institute code           '+' "'+Headers[1].W07+'"  (';
  temp1_str:=IntToHex(ord(Headers[1].W07[1]),2)+' '+
             IntToHex(ord(Headers[1].W07[2]),2)+' '+
             IntToHex(ord(Headers[1].W07[3]),2)+' '+
             IntToHex(ord(Headers[1].W07[4]),2);
  line_str:=line_str+temp1_str+') ';
  if Test_Spacje_OK(Headers[1].W07) then
    begin {Spacje OK}
      il_problemow:=0;
      doy:=2;
      repeat
        if  Headers[doy].W07<>Headers[1].W07 then
          begin
            il_problemow:=il_problemow+1;
            line_str:=line_str+'unexpected change    W07='+Headers[doy].W07+'    day_of_year='+Leading_Zero(doy,3);
          end;
        doy:=doy+1;
      until ((doy=Max_day+1) or (il_problemow>0));
    end {Spacje OK}
  else
    begin {Spacje not OK}
      line_str:=line_str+'A string shorter than 4 chars should be padded to the left with spaces (http://www.intermagnet.org/data-donnee/formats/iaf-eng.php)';
    end; {Spacje not OK}
  writeln(fraport,line_str);
end; {Procedure Check_W07}


Procedure Check_W08;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W08}
  line_str:='';
  line_str:=line_str+'W08 D-conversion factor      '+Leading_Space(Headers[1].W08,7)+'  (';
  temp1_str:=IntToHex(Headers[1].W08,8);
  temp1_str:=Rewer_Hex(temp1_str);
  Insert(' ', temp1_str, 3);
  Insert(' ', temp1_str, 6);
  Insert(' ', temp1_str, 9);
  line_str:=line_str+temp1_str+') ';
  il_problemow:=0;
  doy:=2;
  repeat
    if  (Headers[doy].W08<>Headers[1].W08) then
      begin
        il_problemow:=il_problemow+1;
        line_str:=line_str+'unexpected change    W08='+Leading_Space(Headers[doy].W08,7)+'    day_of_year='+Leading_Zero(doy,3);
      end;
    doy:=doy+1;
  until ((doy=Max_day+1) or (il_problemow>0));
  writeln(fraport,line_str);
  if (((Headers[1].W06='XYZG') or (Trim(Headers[1].W06)='XYZ')) and (Headers[1].W08<>10000)) then
    begin
      line_str:='                              D-conversion factor should be exactly 10000 for W06 = XYZG or XYZ';
      writeln(fraport,line_str);
    end;
end; {Procedure Check_W08}


Procedure Check_W09;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W09}
  line_str:='';
  line_str:=line_str+'W09 Data quality code        '+' "'+Headers[1].W09+'"  (';
  temp1_str:=IntToHex(ord(Headers[1].W09[1]),2)+' '+
             IntToHex(ord(Headers[1].W09[2]),2)+' '+
             IntToHex(ord(Headers[1].W09[3]),2)+' '+
             IntToHex(ord(Headers[1].W09[4]),2);
  line_str:=line_str+temp1_str+') ';
  if Test_Spacje_OK(Headers[1].W09) then
    begin {Spacje OK}
      il_problemow:=0;
      doy:=2;
      repeat
        if  Headers[doy].W09<>Headers[1].W09 then
          begin
            il_problemow:=il_problemow+1;
            line_str:=line_str+'unexpected change    W09='+Headers[doy].W09+'    day_of_year='+Leading_Zero(doy,3);
          end;
        doy:=doy+1;
      until ((doy=Max_day+1) or (il_problemow>0));
    end {Spacje OK}
  else
    begin {Spacje not OK}
      line_str:=line_str+'A string shorter than 4 chars should be padded to the left with spaces (http://www.intermagnet.org/data-donnee/formats/iaf-eng.php)';
    end; {Spacje not OK}
  writeln(fraport,line_str);
end; {Procedure Check_W09}


Procedure Check_W10;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W10}
  line_str:='';
  line_str:=line_str+'W10 Instrument code          '+' "'+Headers[1].W10+'"  (';
  temp1_str:=IntToHex(ord(Headers[1].W10[1]),2)+' '+
             IntToHex(ord(Headers[1].W10[2]),2)+' '+
             IntToHex(ord(Headers[1].W10[3]),2)+' '+
             IntToHex(ord(Headers[1].W10[4]),2);
  line_str:=line_str+temp1_str+') ';
  if Test_Spacje_OK(Headers[1].W10) then
    begin {Spacje OK}
      il_problemow:=0;
      doy:=2;
      repeat
        if  Headers[doy].W10<>Headers[1].W10 then
          begin
            il_problemow:=il_problemow+1;
            line_str:=line_str+'unexpected change    W10='+Headers[doy].W10+'    day_of_year='+Leading_Zero(doy,3);
          end;
        doy:=doy+1;
      until ((doy=Max_day+1) or (il_problemow>0));
    end {Spacje OK}
  else
    begin {Spacje not OK}
      line_str:=line_str+'A string shorter than 4 chars should be padded to the left with spaces (http://www.intermagnet.org/data-donnee/formats/iaf-eng.php)';
    end; {Spacje not OK}
  if ((Headers[1].W10='    ') and (il_problemow=0)) then
    line_str:=line_str+' Could you fill in this field, please';
  writeln(fraport,line_str);
end; {Procedure Check_W10}


Procedure Check_W11;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W11}
  line_str:='';
  line_str:=line_str+'W11 Limit for K9             '+Leading_Space(Headers[1].W11,7)+'  (';
  temp1_str:=IntToHex(Headers[1].W11,8);
  temp1_str:=Rewer_Hex(temp1_str);
  Insert(' ', temp1_str, 3);
  Insert(' ', temp1_str, 6);
  Insert(' ', temp1_str, 9);
  line_str:=line_str+temp1_str+') ';
  il_problemow:=0;
  doy:=2;
  repeat
    if  (Headers[doy].W11<>Headers[1].W11) then
      begin
        il_problemow:=il_problemow+1;
        line_str:=line_str+'unexpected change    W11='+Leading_Space(Headers[doy].W11,7)+'    day_of_year='+Leading_Zero(doy,3);
      end;
    doy:=doy+1;
  until ((doy=Max_day+1) or (il_problemow>0));
  writeln(fraport,line_str);
  if ((Headers[1].W11=0) or ((Headers[1].W11>=200) and (Headers[1].W11<=3000))) then
    begin
      {realistic K9 limit - nothing to do}
    end
  else
    begin
      {unrealistic - warning}
      line_str:='                              WARNING! Unrealistic Limit for K9';
      writeln(fraport,line_str);
    end;
end; {Procedure Check_W11}


Procedure Check_W12;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W12}
  line_str:='';
  line_str:=line_str+'W12 Sample period (ms)       '+Leading_Space(Headers[1].W12,7)+'  (';
  temp1_str:=IntToHex(Headers[1].W12,8);
  temp1_str:=Rewer_Hex(temp1_str);
  Insert(' ', temp1_str, 3);
  Insert(' ', temp1_str, 6);
  Insert(' ', temp1_str, 9);
  line_str:=line_str+temp1_str+') ';
  il_problemow:=0;
  doy:=2;
  repeat
    if  (Headers[doy].W12<>Headers[1].W12) then
      begin
        il_problemow:=il_problemow+1;
        line_str:=line_str+'unexpected change    W12='+Leading_Space(Headers[doy].W12,7)+'    day_of_year='+Leading_Zero(doy,3);
      end;
    doy:=doy+1;
  until ((doy=Max_day+1) or (il_problemow>0));
  writeln(fraport,line_str);
  if ((Headers[1].W12>=10) and (Headers[1].W12<=10000)) then
    begin
      {realistic Sample period - nothing to do}
    end
  else
    begin
      {unrealistic - warning}
      line_str:='                                                        Please check whether Sample period in ms is OK';
      writeln(fraport,line_str);
    end;
end; {Procedure Check_W12}


Procedure Check_W13;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W13}
  line_str:='';
  line_str:=line_str+'W13 Sensor orientation       '+' "'+Headers[1].W13+'"  (';
  temp1_str:=IntToHex(ord(Headers[1].W13[1]),2)+' '+
             IntToHex(ord(Headers[1].W13[2]),2)+' '+
             IntToHex(ord(Headers[1].W13[3]),2)+' '+
             IntToHex(ord(Headers[1].W13[4]),2);
  line_str:=line_str+temp1_str+') ';
  if Test_Spacje_OK(Headers[1].W13) then
    begin {Spacje OK}
      il_problemow:=0;
      doy:=2;
      repeat
        if  Headers[doy].W13<>Headers[1].W13 then
          begin
            il_problemow:=il_problemow+1;
            line_str:=line_str+'unexpected change    W13='+Headers[doy].W13+'    day_of_year='+Leading_Zero(doy,3);
          end;
        doy:=doy+1;
      until ((doy=Max_day+1) or (il_problemow>0));
    end {Spacje OK}
  else
    begin {Spacje not OK}
      line_str:=line_str+'A string shorter than 4 chars should be padded to the left with spaces (http://www.intermagnet.org/data-donnee/formats/iaf-eng.php)';
    end; {Spacje not OK}
  writeln(fraport,line_str);
end; {Procedure Check_W13}


Procedure Check_W14;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W14}
  line_str:='';
  temp1_str:=IntToHex(ord(Headers[1].W14[1]),2)+' '+
             IntToHex(ord(Headers[1].W14[2]),2)+' '+
             IntToHex(ord(Headers[1].W14[3]),2)+' '+
             IntToHex(ord(Headers[1].W14[4]),2);
  if temp1_str='00 00 00 00' then
    line_str:=line_str+'W14 Publication date         '+' "    "  ('
  else
    line_str:=line_str+'W14 Publication date         '+' "'+Headers[1].W14+'"  (';
  temp1_str:=IntToHex(ord(Headers[1].W14[1]),2)+' '+
             IntToHex(ord(Headers[1].W14[2]),2)+' '+
             IntToHex(ord(Headers[1].W14[3]),2)+' '+
             IntToHex(ord(Headers[1].W14[4]),2);
  line_str:=line_str+temp1_str+') ';
  if Test_Spacje_OK(Headers[1].W14) then
    begin {Spacje OK}
      il_problemow:=0;
      doy:=2;
      repeat
        if  Headers[doy].W14<>Headers[1].W14 then
          begin
            il_problemow:=il_problemow+1;
            line_str:=line_str+'unexpected change    W14='+Headers[doy].W14+'    day_of_year='+Leading_Zero(doy,3);
          end;
        doy:=doy+1;
      until ((doy=Max_day+1) or (il_problemow>0));
    end {Spacje OK}
  else
    begin {Spacje not OK}
    end; {Spacje not OK}
    if il_problemow=0 then
      line_str:=line_str+'Date of acceptation as Definitive - will be set by INTERMAGNET';
  writeln(fraport,line_str);
end; {Procedure Check_W14}


Procedure Check_W15;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W15}
  line_str:='';
  line_str:=line_str+'W15 Format version          ';
  Case (Headers[1].W15) and $000000ff of
    0    : begin
             line_str:=line_str+' ver 1.0'
           end;
    1    : begin
             line_str:=line_str+' ver 1.1'
           end;
    2    : begin
             line_str:=line_str+' ver 2.0'
           end;
    3    : begin
             line_str:=line_str+' ver 2.1'
           end;
    else   begin
             line_str:=line_str+' unknown'
           end;
  end;
  line_str:=line_str+'  (';
  temp1_str:=IntToHex(Headers[1].W15,8);
  temp1_str:=Rewer_Hex(temp1_str);
  Insert(' ', temp1_str, 3);
  Insert(' ', temp1_str, 6);
  Insert(' ', temp1_str, 9);
  line_str:=line_str+temp1_str+') ';
  if Headers[1].W15<>3 then
    begin
      line_str:=line_str+'ver 2.1 is obligatory 2010 onwards, ';
    end;
  il_problemow:=0;
  doy:=2;
  repeat
    if  (Headers[doy].W15<>Headers[1].W15) then
      begin
        il_problemow:=il_problemow+1;
        line_str:=line_str+'doy='+Leading_Zero(doy,3)+' W15='+Leading_Space(Headers[doy].W15,7)+' ( ! unexpected change)';
      end;
    doy:=doy+1;
  until ((doy=Max_day+1) or (il_problemow>0));
  writeln(fraport,line_str);
  if ((Headers[1].W15) and $000000ff)>3 then
    begin
      {wrong W15}
      line_str:='                              W15 is set unproperly - Format version is unknown';
      writeln(fraport,line_str);
    end
  else
    begin
      {Right W15}
    end;
end; {Procedure Check_W15}


Procedure Check_W16;
var doy:integer;
    line_str:string250;
    temp1_str:string250;
    il_problemow:integer;
    doy_problem:integer;
begin {Procedure Check_W16}
  line_str:='';
  line_str:=line_str+'W16 Reserved word            '+Leading_Space(Headers[1].W16,7)+'  (';
  temp1_str:=IntToHex(Headers[1].W16,8);
  temp1_str:=Rewer_Hex(temp1_str);
  Insert(' ', temp1_str, 3);
  Insert(' ', temp1_str, 6);
  Insert(' ', temp1_str, 9);
  line_str:=line_str+temp1_str+') ';
  il_problemow:=0;
  doy:=2;
  repeat
    if  (Headers[doy].W16<>Headers[1].W16) then
      begin
        il_problemow:=il_problemow+1;
        line_str:=line_str+'unexpected change    W01='+Headers[doy].W01+'    day_of_year='+Leading_Zero(doy,3);
        line_str:=line_str+'doy='+Leading_Zero(doy,3)+' W16='+Leading_Space(Headers[doy].W16,7)+' ( ! unexpected change)';
      end;
    doy:=doy+1;
  until ((doy=Max_day+1) or (il_problemow>0));
  writeln(fraport,line_str);
end; {Procedure Check_W16}




begin {Procedure Check_Headers}
  Check_W01;
  Check_W02;
  Check_W03;
  Check_W04;
  Check_W05;
  Check_W06;
  Check_W07;
  Check_W08;
  Check_W09;
  Check_W10;
  Check_W11;
  Check_W12;
  Check_W13;
  Check_W14;
  Check_W15;
  Check_W16;
end; {Procedure Check_Headers}


Procedure Read_XYZF_from_yearmean;
var fyear:text;
    fil_str:string250;
    line_str:string250;
    temp1_str,temp2_str:string250;
    X_str,Y_str,Z_str,F_str:string250;
    code:integer;
begin {Procedure Read_XYZF_from_yearmean}
  X_yearmean:=999999.0;
  Y_yearmean:=999999.0;
  Z_yearmean:=999999.0;
  F_yearmean:=999999.0;
  temp1_str:=dir_iaf_str+'\yearmean.'+IMO_str;
  if Detect_system_EOL(temp1_str)=1 then
    begin
      Kopiuj1(temp1_str,'tmp_check1min.tmp');
    end
  else
    begin
      Text_Any_System_to_Windows(temp1_str,'tmp_check1min.tmp');
    end;
  fil_str:='tmp_check1min.tmp';
  AssignFile(fyear,fil_str);
  reset(fyear);
  while not eof(fyear) do
    begin
      readln(fyear,line_str);
      temp1_str:=Wytnij(line_str,0);
      temp1_str:=copy(temp1_str,1,4);
      if temp1_str=year_str then
        begin {if temp1_str=year_str then}
           temp2_str:=Wytnij(line_str,10);
           if temp2_str='A' then
             begin
               {X}
               X_str:=Wytnij(line_str,6);
               Val(X_str,X_yearmean,code);
               if code<>0 then X_yearmean:=999999.0;
               {Y}
               Y_str:=Wytnij(line_str,7);
               Val(Y_str,Y_yearmean,code);
               if code<>0 then Y_yearmean:=999999.0;
               {Z}
               Z_str:=Wytnij(line_str,8);
               Val(Z_str,Z_yearmean,code);
               if code<>0 then Z_yearmean:=999999.0;
               {F}
               F_str:=Wytnij(line_str,9);
               Val(F_str,F_yearmean,code);
               if code<>0 then F_yearmean:=999999.0;
             end;
        end; {if temp1_str=year_str then}
    end;
  CloseFile(fyear);
  DeleteFile('tmp_check1min.tmp');
end; {Procedure Read_XYZF_from_yearmean}



Procedure Read_HF_from_BLV;
var fblv:text;
    fil_str:string250;
    line_str:string250;
    temp1_str,temp2_str:string250;
    H_str,F_str:string250;
    code:integer;
begin {Procedure Read_HF_from_BLV}
  H_BLV:=999999.0;
  F_BLV:=999999.0;
  temp1_str:=dir_iaf_str+'\'+IMO_str+year_str+'.blv';
  if Detect_system_EOL(temp1_str)=1 then
    begin
      Kopiuj1(temp1_str,'tmp_check1min.tmp');
    end
  else
    begin
      Text_Any_System_to_Windows(temp1_str,'tmp_check1min.tmp');
    end;
  fil_str:='tmp_check1min.tmp';
  AssignFile(fblv,fil_str);
  reset(fblv);
  readln(fblv,line_str);
  {H}
  H_str:=Wytnij(line_str,1);
  Val(H_str,H_BLV,code);
  if code<>0 then H_BLV:=999999.0;
  {F}
  F_str:=Wytnij(line_str,2);
  Val(F_str,F_BLV,code);
  if code<>0 then F_BLV:=999999.0;
  CloseFile(fblv);
  DeleteFile('tmp_check1min.tmp');
end; {Procedure Read_HF_from_BLV}



Procedure Message_if_text_no_Windows;
var temp1_str:string250;
    sys:integer;
begin {Procedure Message_if_text_no_Windows}
  {yearmean.cod}
  if yearmean_file_present then
    begin {if yearmean_file_present then}
      temp1_str:=dir_iaf_str+'\yearmean.'+IMO_str;
      sys:=Detect_system_EOL(temp1_str);
      case sys of
        0:    begin
                writeln(fraport,'WARNING: Not recognized EOL (end of line) chars in ',temp1_str,' (should be CrLf) -  please fix this problem');
                yearmean_EOL:=0;
              end;
        1:    begin
                {CrLf - OK - nothing to do}
                yearmean_EOL:=1;
              end;
        2:    begin
                writeln(fraport,'WARNING: EOL (end of line) = Cr in ',temp1_str,' (should be CrLf) -  please fix this problem');
                yearmean_EOL:=2;
              end;
        3:    begin
                writeln(fraport,'WARNING: EOL (end of line) = Lf in ',temp1_str,' (should be CrLf) -  please fix this problem');
                yearmean_EOL:=3;
              end;
        else  begin
                writeln(fraport,'WARNING: Not recognized EOL (end of line) chars in ',temp1_str,' (should be CrLf) -  please fix this problem');
                yearmean_EOL:=0;
              end;
      end;
    end; {if yearmean_file_present then}


  {codyyyy.blv}
  if blv_present then
    begin {if blv_present then}
      temp1_str:=dir_iaf_str+'\'+IMO_str+year_str+'.blv';
      sys:=Detect_system_EOL(temp1_str);
      case sys of
        0:    begin
                writeln(fraport,'WARNING: Not recognized EOL (end of line) chars in ',temp1_str,' (should be CrLf) -  please fix this problem');
                BLV_EOL:=0;
              end;
        1:    begin
                {CrLf - OK - nothing to do}
                BLV_EOL:=1;
              end;
        2:    begin
                writeln(fraport,'WARNING: EOL (end of line) = Cr in ',temp1_str,' (should be CrLf) -  please fix this problem');
                BLV_EOL:=2;
              end;
        3:    begin
                writeln(fraport,'WARNING: EOL (end of line) = Lf in ',temp1_str,' (should be CrLf) -  please fix this problem');
                BLV_EOL:=3;
              end;
        else  begin
                writeln(fraport,'WARNING: Not recognized EOL (end of line) chars in ',temp1_str,' (should be CrLf) -  please fix this problem');
                BLV_EOL:=0;
              end;
      end;
    end; {if blv_present then}


  {readme.cod}
  if ReadmeIMO_present then
    begin {if ReadmeIMO_present then}
      temp1_str:=dir_iaf_str+'\readme.'+IMO_str;
      sys:=Detect_system_EOL(temp1_str);
      case sys of
        0:    begin
                writeln(fraport,'WARNING: Not recognized EOL (end of line) chars in ',temp1_str,' (should be CrLf) -  please fix this problem');
                ReadmeIMO_EOL:=0;
              end;
        1:    begin
               {CrLf - OK - nothing to do}
                ReadmeIMO_EOL:=1;
              end;
        2:    begin
                writeln(fraport,'WARNING: EOL (end of line) = Cr in ',temp1_str,' (should be CrLf) -  please fix this problem');
                ReadmeIMO_EOL:=2;
              end;
        3:    begin
                writeln(fraport,'WARNING: EOL (end of line) = Lf in ',temp1_str,' (should be CrLf) -  please fix this problem');
                ReadmeIMO_EOL:=3;
              end;
        else  begin
                writeln(fraport,'WARNING: Not recognized EOL (end of line) chars in ',temp1_str,' (should be CrLf) -  please fix this problem');
                ReadmeIMO_EOL:=0;
              end;
      end;
    end; {if ReadmeIMO_present then}

  writeln(fraport);

end; {Procedure Message_if_text_no_Windows}



Procedure Calculations_yearly_daily_hourly_means;
{
1. Hourly mean values:
    The hourly mean values should be processed following the IAGA rule.
     - Arithmetic average of the 1-minute data,
     - Centered on the centre of the hour which is defined by minutes 00-59 of that hour.
2. Daily mean values:
     - Arithmetic average of the 1-minute data,
     - Centered on the centre of the day defined by 00:00-23:59.
3. Annual mean values:
     - Arithmetic average of the 1-minute data,
     - Centered on the centre of the year defined by the dates between 01 Jan 00:00 – 31 Dec 23:59.
4. Missing values
     In case of missing 1-minute data, hourly, daily, and annual mean values
     are processed only if at least 90% of the considered 1-minute data does exist.
}
var temp1_str:string250;
    min:integer;
    hour:integer;
    day:integer;
    suma:Int64;
    licz:integer;
    temp_real:real;
    i:integer;
begin {Procedure Calculations_yearly_daily_hourly_means}
  {wstêpne ustawienie srednich na missing}
  XYZG_year_calculated.X:=999999.0; XYZG_year_calculated.Y:=999999.0; XYZG_year_calculated.Z:=999999.0;
  for i:=1 to 366 do
    begin
      XYZG_day_calculated[i].X:=999999.0;
      XYZG_day_calculated[i].Y:=999999.0;
      XYZG_day_calculated[i].Z:=999999.0;
    end;
  for i:=0 to  8783 do
    begin
      XYZG_hour_calculated[i].X:=999999.0;
      XYZG_hour_calculated[i].Y:=999999.0;
      XYZG_hour_calculated[i].Z:=999999.0;
    end;


  {X yearly means}
  licz:=0;
  suma:=0;
  for min:=0 to Max_day*1440-1 do
    begin
      if ((XYZG_minute[min,1]=999999) or (XYZG_minute[min,1]=888888)) then
        begin
        end
      else
        begin
          suma:=suma+XYZG_minute[min,1];
          licz:=licz+1;
        end;
    end;
  if (100.0*(licz/(Max_day*1440)))>=90.0 then
    begin
      temp_real:=Round(suma/licz)/10.0;
    end
  else
    begin
      temp_real:=999999.0;
    end;
  XYZG_year_calculated.X:=temp_real;
  XYZG_year_calculated.lX:=licz;

  {Y yearly means}
  licz:=0;
  suma:=0;
  for min:=0 to Max_day*1440-1 do
    begin
      if ((XYZG_minute[min,2]=999999) or (XYZG_minute[min,2]=888888)) then
        begin
        end
      else
        begin
          suma:=suma+XYZG_minute[min,2];
          licz:=licz+1;
        end;
    end;
  if (100.0*(licz/(Max_day*1440)))>=90.0 then
    begin
      temp_real:=Round(suma/licz)/10.0;
    end
  else
    begin
      temp_real:=999999.0;
    end;
  XYZG_year_calculated.Y:=temp_real;
  XYZG_year_calculated.lY:=licz;

  {Z yearly means}
  licz:=0;
  suma:=0;
  for min:=0 to Max_day*1440-1 do
    begin
      if ((XYZG_minute[min,3]=999999) or (XYZG_minute[min,3]=888888)) then
        begin
        end
      else
        begin
          suma:=suma+XYZG_minute[min,3];
          licz:=licz+1;
        end;
    end;
  if (100.0*(licz/(Max_day*1440)))>=90.0 then
    begin
      temp_real:=Round(suma/licz)/10.0;
    end
  else
    begin
      temp_real:=999999.0;
    end;
  XYZG_year_calculated.Z:=temp_real;
  XYZG_year_calculated.lZ:=licz;


  {X daily means}
  for day:=1 to Max_day do
    begin {for day:=1 to Max_day do}
      licz:=0;
      suma:=0;
      for min:=0 to 1439 do
        begin {for min:=0 to 1439 do}
          if ((XYZG_minute[(day-1)*1440+min,1]=999999) or (XYZG_minute[(day-1)*1440+min,1]=888888)) then
            begin
            end
          else
            begin
              suma:=suma+XYZG_minute[(day-1)*1440+min,1];
              licz:=licz+1;
            end;
        end; {for min:=0 to 1439 do}
      {podsumowanie i zapis doby;
       ENG. summary and writing day}
      if (100.0*(licz/1440))>=90.0 then
        begin
          temp_real:=Round(suma/licz)/10.0;
        end
      else
        begin
          temp_real:=999999.0;
        end;
      XYZG_day_calculated[day].X:=temp_real;
      XYZG_day_calculated[day].lX:=licz;
    end; {for day:=1 to Max_day do}

  {Y daily means}
  for day:=1 to Max_day do
    begin {for day:=1 to Max_day do}
      licz:=0;
      suma:=0;
      for min:=0 to 1439 do
        begin {for min:=0 to 1439 do}
          if ((XYZG_minute[(day-1)*1440+min,2]=999999) or (XYZG_minute[(day-1)*1440+min,2]=888888)) then
            begin
            end
          else
            begin
              suma:=suma+XYZG_minute[(day-1)*1440+min,2];
              licz:=licz+1;
            end;
        end; {for min:=0 to 1439 do}
      {podsumowanie i zapis doby;
       ENG. summary and writing day}
      if (100.0*(licz/1440))>=90.0 then
        begin
          temp_real:=Round(suma/licz)/10.0;
        end
      else
        begin
          temp_real:=999999.0;
        end;
      XYZG_day_calculated[day].Y:=temp_real;
      XYZG_day_calculated[day].lY:=licz;
    end; {for day:=1 to Max_day do}

  {Z daily means}
  for day:=1 to Max_day do
    begin {for day:=1 to Max_day do}
      licz:=0;
      suma:=0;
      for min:=0 to 1439 do
        begin {for min:=0 to 1439 do}
          if ((XYZG_minute[(day-1)*1440+min,3]=999999) or (XYZG_minute[(day-1)*1440+min,3]=888888)) then
            begin
            end
          else
            begin
              suma:=suma+XYZG_minute[(day-1)*1440+min,3];
              licz:=licz+1;
            end;
        end; {for min:=0 to 1439 do}
      {podsumowanie i zapis doby;
       ENG. summary and writing day}
      if (100.0*(licz/1440))>=90.0 then
        begin
          temp_real:=Round(suma/licz)/10.0;
        end
      else
        begin
          temp_real:=999999.0;
        end;
      XYZG_day_calculated[day].Z:=temp_real;
      XYZG_day_calculated[day].lZ:=licz;
    end; {for day:=1 to Max_day do}


  {X hourly means}
  for day:=1 to Max_day do
    begin {for day:=1 to Max_day do}
      for hour:=0 to 23 do
        begin {for hour:=0 to 23 do}
          licz:=0;
          suma:=0;
          for min:=0 to 59 do
            begin {for min:=0 to 59 do}
              if ((XYZG_minute[(day-1)*1440+hour*60+min,1]=999999) or (XYZG_minute[(day-1)*1440+hour*60+min,1]=888888)) then
                begin
                end
              else
                begin
                  suma:=suma+XYZG_minute[(day-1)*1440+hour*60+min,1];
                  licz:=licz+1;
                end;
            end; {for min:=0 to 59 do}
          {podsumowanie i zapis godziny;
           ENG. summary and writing hour}
          if (100.0*(licz/60))>=90.0 then
            begin
              temp_real:=Round(suma/licz)/10.0;
            end
          else
            begin
              temp_real:=999999.0;
            end;
          XYZG_hour_calculated[(day-1)*24+hour].X:=temp_real;
          XYZG_hour_calculated[(day-1)*24+hour].lX:=licz;
        end; {for hour:=0 to 23 do}
    end; {for day:=1 to Max_day do}

  {Y hourly means}
  for day:=1 to Max_day do
    begin {for day:=1 to Max_day do}
      for hour:=0 to 23 do
        begin {for hour:=0 to 23 do}
          licz:=0;
          suma:=0;
          for min:=0 to 59 do
            begin {for min:=0 to 59 do}
              if ((XYZG_minute[(day-1)*1440+hour*60+min,2]=999999) or (XYZG_minute[(day-1)*1440+hour*60+min,2]=888888)) then
                begin
                end
              else
                begin
                  suma:=suma+XYZG_minute[(day-1)*1440+hour*60+min,2];
                  licz:=licz+1;
                end;
            end; {for min:=0 to 59 do}
          {podsumowanie i zapis godziny;
           ENG. summary and writing hour}
          if (100.0*(licz/60))>=90.0 then
            begin
              temp_real:=Round(suma/licz)/10.0;
            end
          else
            begin
              temp_real:=999999.0;
            end;
          XYZG_hour_calculated[(day-1)*24+hour].Y:=temp_real;
          XYZG_hour_calculated[(day-1)*24+hour].lY:=licz;
        end; {for hour:=0 to 23 do}
    end; {for day:=1 to Max_day do}

  {Z hourly means}
  for day:=1 to Max_day do
    begin {for day:=1 to Max_day do}
      for hour:=0 to 23 do
        begin {for hour:=0 to 23 do}
          licz:=0;
          suma:=0;
          for min:=0 to 59 do
            begin {for min:=0 to 59 do}
              if ((XYZG_minute[(day-1)*1440+hour*60+min,3]=999999) or (XYZG_minute[(day-1)*1440+hour*60+min,3]=888888)) then
                begin
                end
              else
                begin
                  suma:=suma+XYZG_minute[(day-1)*1440+hour*60+min,3];
                  licz:=licz+1;
                end;
            end; {for min:=0 to 59 do}
          {podsumowanie i zapis godziny}
          if (100.0*(licz/60))>=90.0 then
            begin
              temp_real:=Round(suma/licz)/10.0;
            end
          else
            begin
              temp_real:=999999.0;
            end;
          XYZG_hour_calculated[(day-1)*24+hour].Z:=temp_real;
          XYZG_hour_calculated[(day-1)*24+hour].lZ:=licz;
        end; {for hour:=0 to 23 do}
    end; {for day:=1 to Max_day do}
end; {Procedure Calculations_yearly_daily_hourly_means}


Procedure ComparisonYearly_IAF_yearmean;
var dX,dY,dZ:real;
begin {Procedure ComparisonYearly_IAF_yearmean}
  writeln(fraport,'                                      X         Y         Z');
  writeln(fraport,'Reported in yearmean file:     ',X_yearmean:10:1,Y_yearmean:10:1,Z_yearmean:10:1);
  writeln(fraport,'Calculated from IAF 1 min:     ',XYZG_year_calculated.X:10:1,XYZG_year_calculated.Y:10:1,XYZG_year_calculated.Z:10:1);

  {dX := yearmean - calculated}
  if ((X_yearmean=999999.0) or (XYZG_year_calculated.X=999999.0)) then
    begin
      dX:=999999.0;
    end
  else
    begin
      dX:=X_yearmean-XYZG_year_calculated.X
    end;

  {dY := yearmean - calculated}
  if ((Y_yearmean=999999.0) or (XYZG_year_calculated.Y=999999.0)) then
    begin
      dY:=999999.0;
    end
  else
    begin
      dY:=Y_yearmean-XYZG_year_calculated.Y
    end;

  {dZ := yearmean - calculated}
  if ((Z_yearmean=999999.0) or (XYZG_year_calculated.Z=999999.0)) then
    begin
      dZ:=999999.0;
    end
  else
    begin
      dZ:=Z_yearmean-XYZG_year_calculated.Z
    end;

  writeln(fraport,'Difference:                    ',dX:10:1,dY:10:1,dZ:10:1);
  writeln(fraport);
  writeln(fraport);
end; {Procedure ComparisonYearly_IAF_yearmean}


Procedure Check_Daily_mean_reported2;
var dX,dY,dZ:real;
    day:integer;
    date0 : TDateTime;
    datea : TDateTime;
    temp1_str:string250;
    found_problems:integer;
    drukowac:integer;
    Ta,Tb:boolean;
begin {Procedure Check_Daily_mean_reported2}
  drukowac:=0;
  found_problems:=0;
  Date0:=EncodeDateTime(year,1,1,0,0,0,0);
  if IAF_present then
    begin
      writeln(fraport); writeln(fraport,'COMPARISON '+year_str+' DAILY MEANS reported in '+IMO_str+copy(year_str,3,2)+'???.bin and calculated from 1 min data (displayed >=0.2nT)');
      writeln(fraport,'                                          X         Y         Z');
    end;
  for day:=1 to Max_day do
    begin {for day:=1 to Max_day do}
      drukowac:=0;
      if ((XYZG_day[day,1]=999999) or (XYZG_day[day,1]=888888) or (XYZG_day_calculated[day].X=999999.0)) then
        begin
          dX:=999999.0;
        end
      else
        begin
          dX:=XYZG_day[day,1]/10.0-XYZG_day_calculated[day].X;
          if abs(dX)>=0.2 then
            drukowac:=drukowac+1;
        end;

      if ((XYZG_day[day,2]=999999) or (XYZG_day[day,2]=888888) or (XYZG_day_calculated[day].Y=999999.0)) then
        begin
          dY:=999999.0;
        end
      else
        begin
          dY:=XYZG_day[day,2]/10.0-XYZG_day_calculated[day].Y;
          if abs(dY)>=0.2 then
            drukowac:=drukowac+1;
        end;

      if ((XYZG_day[day,3]=999999) or (XYZG_day[day,3]=888888) or (XYZG_day_calculated[day].Z=999999.0)) then
        begin
          dZ:=999999.0;
        end
      else
        begin
          dZ:=XYZG_day[day,3]/10.0-XYZG_day_calculated[day].Z;
          if abs(dZ)>=0.2 then
            drukowac:=drukowac+1;
        end;

        if (((XYZG_day[day,1]=999999) or (XYZG_day[day,1]=888888)) and (XYZG_day_calculated[day].X<>999999.0)) then
            drukowac:=drukowac+1;
          if (((XYZG_day[day,2]=999999) or (XYZG_day[day,2]=888888)) and (XYZG_day_calculated[day].Y<>999999.0)) then
            drukowac:=drukowac+1;
          if (((XYZG_day[day,3]=999999) or (XYZG_day[day,3]=888888)) and (XYZG_day_calculated[day].Z<>999999.0)) then
            drukowac:=drukowac+1;

          if ((XYZG_day[day,1]<888888) and (XYZG_day_calculated[day].X=999999.0)) then
            drukowac:=drukowac+1;
          if ((XYZG_day[day,2]<888888) and (XYZG_day_calculated[day].Y=999999.0)) then
            drukowac:=drukowac+1;
          if ((XYZG_day[day,3]<888888) and (XYZG_day_calculated[day].Z=999999.0)) then
            drukowac:=drukowac+1;

      if drukowac>0 then
        begin
          datea:=date0+(day-1);
          temp1_str:=DateToStr(Datea);
          write(fraport,temp1_str,'   ','Reported in IAF:       ');
          if ((XYZG_day[day,1]=999999) or (XYZG_day[day,1]=888888)) then
            write(fraport,1.0*XYZG_day[day,1]:10:1)
          else
            write(fraport,0.1*XYZG_day[day,1]:10:1);
          if ((XYZG_day[day,2]=999999) or (XYZG_day[day,2]=888888)) then
            write(fraport,1.0*XYZG_day[day,2]:10:1)
          else
            write(fraport,0.1*XYZG_day[day,2]:10:1);
          if ((XYZG_day[day,3]=999999) or (XYZG_day[day,3]=888888)) then
            writeln(fraport,1.0*XYZG_day[day,3]:10:1)
          else
            writeln(fraport,0.1*XYZG_day[day,3]:10:1);
          writeln(fraport,'             Calculated from IAF:   ',XYZG_day_calculated[day].X:10:1,XYZG_day_calculated[day].Y:10:1,XYZG_day_calculated[day].Z:10:1);
          if abs(dX)>800000.0 then dX:=999999.0;
          if abs(dY)>800000.0 then dY:=999999.0;
          if abs(dZ)>800000.0 then dZ:=999999.0;
          writeln(fraport,'                      Difference:   ',dX:10:1,dY:10:1,dZ:10:1);
          writeln(fraport);
          found_problems:=found_problems+1;
        end;
    end; {for day:=1 to Max_day do}
  if IAF_present then
    writeln(fraport,'                  Days_when_differences>=0.2nT or other problems: ',found_problems);
  DailyMeans_found_problems:=found_problems;
  writeln(fraport);
end; {Procedure Check_Daily_mean_reported2}



Procedure Check_Hourly_mean_reported2;
var dX,dY,dZ:real;
    day:integer;
    hour:integer;
    date0 : TDateTime;
    datea : TDateTime;
    temp1_str:string250;
    found_problems:integer;
    drukowac:integer;

begin {Procedure Check_Hourly_mean_reported2}
  drukowac:=0;
  found_problems:=0;
  Date0:=EncodeDateTime(year,1,1,0,0,0,0);
  if IAF_present then
    begin
      writeln(fraport); writeln(fraport,'COMPARISON '+year_str+' HOURLY MEANS reported in '+IMO_str+copy(year_str,3,2)+'???.bin and calculated from 1 min data (displayed >=0.2nT)');
      writeln(fraport,'                                               X         Y         Z');
    end;
  for day:=1 to Max_day do
    begin {for day:=1 to Max_day do}
      for hour:=0 to 23 do
        begin {for hour:=0 to 23 do}
          drukowac:=0;
          if ((XYZG_hour[(day-1)*24+hour,1]=999999) or (XYZG_hour[(day-1)*24+hour,1]=888888) or (XYZG_hour_calculated[(day-1)*24+hour].X=999999.0)) then
            begin
              dX:=999999.0;
            end
          else
            begin
              dX:=XYZG_hour[(day-1)*24+hour,1]/10.0-XYZG_hour_calculated[(day-1)*24+hour].X;
              if abs(dX)>=0.2 then
                drukowac:=drukowac+1;
            end;

          if ((XYZG_hour[(day-1)*24+hour,2]=999999) or (XYZG_hour[(day-1)*24+hour,2]=888888) or (XYZG_hour_calculated[(day-1)*24+hour].Y=999999.0)) then
            begin
              dY:=999999.0;
            end
          else
            begin
              dY:=XYZG_hour[(day-1)*24+hour,2]/10.0-XYZG_hour_calculated[(day-1)*24+hour].Y;
              if abs(dY)>=0.2 then
                drukowac:=drukowac+1;
            end;

          if ((XYZG_hour[(day-1)*24+hour,3]=999999) or (XYZG_hour[(day-1)*24+hour,3]=888888) or (XYZG_hour_calculated[(day-1)*24+hour].Z=999999.0)) then
            begin
              dZ:=999999.0;
            end
          else
            begin
              dZ:=XYZG_hour[(day-1)*24+hour,3]/10.0-XYZG_hour_calculated[(day-1)*24+hour].Z;
              if abs(dZ)>=0.2 then
                drukowac:=drukowac+1;
            end;

          if (((XYZG_hour[(day-1)*24+hour,1]=999999) or (XYZG_hour[(day-1)*24+hour,1]=888888)) and (XYZG_hour_calculated[(day-1)*24+hour].X<>999999.0)) then
            drukowac:=drukowac+1;
          if (((XYZG_hour[(day-1)*24+hour,2]=999999) or (XYZG_hour[(day-1)*24+hour,2]=888888)) and (XYZG_hour_calculated[(day-1)*24+hour].Y<>999999.0)) then
            drukowac:=drukowac+1;
          if (((XYZG_hour[(day-1)*24+hour,3]=999999) or (XYZG_hour[(day-1)*24+hour,3]=888888)) and (XYZG_hour_calculated[(day-1)*24+hour].Z<>999999.0)) then
            drukowac:=drukowac+1;

          if ((XYZG_hour[(day-1)*24+hour,1]<888888) and (XYZG_hour_calculated[(day-1)*24+hour].X=999999.0)) then
            drukowac:=drukowac+1;
          if ((XYZG_hour[(day-1)*24+hour,2]<888888) and (XYZG_hour_calculated[(day-1)*24+hour].Y=999999.0)) then
            drukowac:=drukowac+1;
          if ((XYZG_hour[(day-1)*24+hour,3]<888888) and (XYZG_hour_calculated[(day-1)*24+hour].Z=999999.0)) then
            drukowac:=drukowac+1;


          if drukowac>0 then
            begin
              datea:=date0+(day-1);
              temp1_str:=DateToStr(Datea);
              write(fraport,temp1_str,' ',Leading_Zero(hour,2),'-',Leading_Zero(hour+1,2),'  Reported in IAF:       ');
              if ((XYZG_hour[(day-1)*24+hour,1]=999999) or (XYZG_hour[(day-1)*24+hour,1]=888888)) then
                write(fraport,1.0*XYZG_hour[(day-1)*24+hour,1]:10:1)
              else
                write(fraport,0.1*XYZG_hour[(day-1)*24+hour,1]:10:1);
              if ((XYZG_hour[(day-1)*24+hour,2]=999999) or (XYZG_hour[(day-1)*24+hour,2]=888888)) then
                write(fraport,1.0*XYZG_hour[(day-1)*24+hour,2]:10:1)
              else
                write(fraport,0.1*XYZG_hour[(day-1)*24+hour,2]:10:1);
              if ((XYZG_hour[(day-1)*24+hour,3]=999999) or (XYZG_hour[(day-1)*24+hour,3]=888888)) then
                writeln(fraport,1.0*XYZG_hour[(day-1)*24+hour,3]:10:1)
              else
                writeln(fraport,0.1*XYZG_hour[(day-1)*24+hour,3]:10:1);
              writeln(fraport,'                  Calculated from IAF:   ',XYZG_hour_calculated[(day-1)*24+hour].X:10:1,XYZG_hour_calculated[(day-1)*24+hour].Y:10:1,XYZG_hour_calculated[(day-1)*24+hour].Z:10:1);
              if abs(dX)>800000.0 then dX:=999999.0;
              if abs(dY)>800000.0 then dY:=999999.0;
              if abs(dZ)>800000.0 then dZ:=999999.0;
              writeln(fraport,'                           Difference:   ',dX:10:1,dY:10:1,dZ:10:1);
              writeln(fraport);
              found_problems:=found_problems+1;
            end;
        end; {for hour:=0 to 23 do}
    end; {for day:=1 to Max_day do}
  if IAF_present then
    writeln(fraport,'                  Hours_when_differences>=0.2nT or other problems: ',found_problems);
  HourlyMeans_found_problems:=found_problems;
  writeln(fraport);
end; {Procedure Check_Hourly_mean_reported2}


Procedure Call_ymchk;
var temp1_str:string250;
    director_str:string250;
    IAG_str:string250;
begin {Procedure Call_ymchk}
  writeln(fraport);
  writeln(fraport,'=================== Checking yearmean.imo ============================');
  ymchk;
end; {Procedure Call_ymchk}


Procedure Check_BLV;
var file_BLV_str:string250;
    line_str:string250;
    temp1_str:string250;
    fblv:text;
    code:integer;
    H_int:integer;
    F_int:integer;
    H_iaf:real;
    F_iaf:real;
    year_blv:integer;
    stars:integer;
    fchar:file of char;
    fileContent:string;
    temp_Content:string;
    c: char;
    Len,n:integer;
    i:integer;
    Pos_star2:integer; {pozycja 2-giej gwiazdki w pliku BLV traktowanym, jako file of char}
    pos1,pos2,pos3,pos4,pos5,pos6:integer;

begin {Procedure Check_BLV}
  if BLV_EOL=1 then
    begin
      file_BLV_str:=Dir_iaf_str+'\'+IMO_str+year_str+'.blv';
    end
  else
    begin
      Text_Any_System_to_Windows(Dir_iaf_str+'\'+IMO_str+year_str+'.blv','tmp_check1min.tmp');
      file_BLV_str:='tmp_check1min.tmp';
    end;

  {Sprawdzenie header}
  AssignFile(fblv,file_BLV_str);
  reset(fblv);
  readln(fblv,line_str);
  {H}
  temp1_str:=copy(line_str,6,5);
  val(temp1_str,H_int,code);
  if code<>0 then
    begin
      writeln(fraport,'Error - please check annual H in the header of BLV');
    end
  else
    begin
      if  ((XYZG_year_calculated.X<>999999) and (XYZG_year_calculated.Y<>999999)) then
        begin
          H_iaf:=XYZG_year_calculated.X*XYZG_year_calculated.X+XYZG_year_calculated.Y*XYZG_year_calculated.Y;
          H_iaf:=sqrt(H_iaf);
        end
      else
        begin
          H_iaf:=99999.0;
        end;

      if Abs(H_iaf-H_int)>2.0 then
        begin
          writeln(fraport,'Annual H calculated from IAF: ',H_iaf:9:1);
          if H_iaf<>99999.0 then
            writeln(fraport,'Annual H in the header of BLV:',H_int:7)
          else
            writeln(fraport,'Annual H in the header of BLV:',H_int:7,' (should be consistent with yearmean.imo, 99999 is unallowable)');
        end;
    end;

  {F}
  temp1_str:=copy(line_str,12,5);
  val(temp1_str,F_int,code);
  if code<>0 then
    begin
      writeln(fraport,'Error - please check annual F in the header of BLV');
    end
  else
    begin
      if  ((XYZG_year_calculated.X<>999999) and (XYZG_year_calculated.Y<>999999) and (XYZG_year_calculated.Z<>999999)) then
        begin
          F_iaf:=XYZG_year_calculated.X*XYZG_year_calculated.X+XYZG_year_calculated.Y*XYZG_year_calculated.Y+XYZG_year_calculated.Z*XYZG_year_calculated.Z;
          F_iaf:=sqrt(F_iaf);
        end
      else
        begin
          F_iaf:=99999.0;
        end;

      if Abs(F_iaf-F_int)>2.0 then
        begin
          writeln(fraport,'Annual F calculated from IAF: ',F_iaf:11:1);
          if F_iaf<>99999.0 then
            writeln(fraport,'Annual F in the header of BLV:',F_int:9)
          else
            writeln(fraport,'Annual F in the header of BLV:',F_int:9,' (should be consistent with yearmean.imo, 99999 is unallowable)');
        end;
    end;

  {year}
  temp1_str:=copy(line_str,22,4);
  val(temp1_str,year_blv,code);
  if (code<>0) then
    begin
      writeln(fraport,'Error - year is wrong or position is not proper in the header of BLV - please check');
    end
  else
    begin
      if year_blv<>year then
        begin
          writeln(fraport,'Error - year in BLV is ',year_blv,', but should be ',year, ' - please check');
        end;
    end;

  {kod IAGA}
  temp1_str:=copy(line_str,18,3);
  if AnsiCompareText(temp1_str,IMO_str)<>0 then
    begin
      writeln(fraport,'Error - please check whether IAGA code is correct');
    end;

  {Czy s¹ 2 gwiazdki}
  stars:=0;
  while not eof(fblv) do
    begin
      readln(fblv,line_str);
      if copy(line_str,1,1)='*' then
        stars:=stars+1;
    end;
  close(fblv);


  {Sprawdzenie, czy jest jakikolwiek komentarz po 2-giej gwiazdce}
  if stars=2 then
    begin {stars=2}
      AssignFile(fchar,file_BLV_str);
      reset(fchar);
      Len := FileSize(fchar);
      n:=Len;
      while n > 0 do
        begin
          Read(fchar, c);
          fileContent := fileContent + c;
          dec(n);
        end;
      CloseFile(fchar);
      Pos_star2:=PosEx('*',fileContent,1);
      Pos_star2:=PosEx('*',fileContent,Pos_star2+1);

      {poszukiwanie slowa 'adopt' po 2-giej gwiazdce;
       ENG. looking for the text 'adopt' after second '*'}
      temp_Content:=fileContent;
      temp_Content:=AnsiLowerCase(temp_Content);
      pos1:=PosEx('adopt',temp_Content,Pos_star2+1);
      pos2:=PosEx('spline',temp_Content,Pos_star2+1);
      pos3:=PosEx('interpolation',temp_Content,Pos_star2+1);
      pos4:=PosEx('polynomial',temp_Content,Pos_star2+1);
      pos5:=PosEx('baseline',temp_Content,Pos_star2+1);

      if ((pos1=0) and (pos2=0) and (pos3=0) and (pos4=0) and (pos5=0))  then
        begin
          writeln(fraport,'Warning - please check the Comments section (after 2-nd star)');
          writeln(fraport,'     Comments section should at least contain a description,');
          writeln(fraport,'     how adopted baseline were determined');
        end;
    end  {stars=2}
  else
    begin {stars<>2}
      writeln(fraport,'WARNING! Not found exactly 2 stars or stars are in wrong positions');
    end; {stars<>2}

  if BLV_EOL<>1 then
    begin
      DeleteFile('tmp_check1min.tmp');
    end;
  writeln(fraport);
end; {Procedure Check_BLV}


Procedure Check_K_indices;
{
zostanie sprawdzone, czy ((K = 0..90) or (K = 999))
}
var doy:integer; {dzien roku liczac od 1}
    found_error:boolean;
    doy_error:integer;
    ii:integer;
    i_temp:integer;
    temp1_str:string250;
    t1_str,t2_str,t3_str,t4_str,t5_str,t6_str,t7_str,t8_str:string8;
    temp_date, temp_date_error:TDateTime;
    ilosc_indeksow:integer;
begin {Procedure Check_K_indices}
  found_error:=FALSE;
  ilosc_indeksow:=0;
  temp_date:=EncodeDate(year-1, 12, 31);
  for doy:=1 to MaX_Day do
    begin
      temp_date:=IncDay(temp_date,1);
      for ii:=1 to 8 do
        begin {for ii:=1 to 8 do}
          i_temp:=ii;
          if found_error=FALSE then
            begin {if found_error=FALSE}
              if not (((indices[doy,ii]>=0) and (indices[doy,ii]<=90)) or (indices[doy,ii]=999)) then
                begin
                  found_error:=TRUE;
                  temp_date_error:=temp_date;
                  doy_error:=doy;
                end
              else
                begin
                  if ((indices[doy,ii]>=0) and (indices[doy,ii]<=90)) then
                    begin
                      ilosc_indeksow:=ilosc_indeksow+1;
                    end;
                end;
            end; {if found_error=FALSE}
        end; {for ii:=1 to 8 do}
    end;
  if found_error=TRUE then
    begin {if found_error=TRUE}
      temp1_str:='K indices out of allowed range (allowed 00..90, 999-missing)';
      writeln(fraport,temp1_str);
      temp1_str:=DateToStr(temp_date_error);
      write(fraport,'First found error:     Date=', temp1_str,'    Kindices = ');
      Str(indices[doy_error,1]:4, t1_str);
      Str(indices[doy_error,2]:4, t2_str);
      Str(indices[doy_error,3]:4, t3_str);
      Str(indices[doy_error,4]:4, t4_str);
      Str(indices[doy_error,5]:4, t5_str);
      Str(indices[doy_error,6]:4, t6_str);
      Str(indices[doy_error,7]:4, t7_str);
      Str(indices[doy_error,8]:4, t8_str);
      temp1_str:=t1_str+t2_str+t3_str+t4_str+t5_str+t6_str+t7_str+t8_str;
      writeln(fraport,temp1_str);
      writeln(fraport);
    end {if found_error=TRUE}
  else
    begin {found_error=FALSE}
      Str(100*ilosc_indeksow/(Max_day*8):6:2, temp1_str);
      temp1_str:='     Percentage of K indices = '+temp1_str+'%';
      writeln(fraport, temp1_str);
    end; {found_error=FALSE}
  writeln(fraport);
end; {Procedure Check_K_indices}



Procedure Check_ReadmeIMO_Year_Header;
var file_ReadmeIMO_str:string250;
    line_str:string250;
    temp1_str:string250;
    freadmeIMO:text;
    code:integer;
    found:boolean;
    pos:integer;
    i:integer;
    year_header:integer; {year header readme.imo}
    colatitude:real;
begin {Procedure Check_ReadmeIMO_Year_Header}
  if ReadmeIMO_EOL=1 then
    begin
      file_ReadmeIMO_str:=Dir_iaf_str+'\readme.'+IMO_str;
    end
  else
    begin
      Text_Any_System_to_Windows(Dir_iaf_str+'\readme.'+IMO_str,'tmp_check1min.tmp');
      file_ReadmeIMO_str:='tmp_check1min.tmp';
    end;


  i:=0;
  AssignFile(freadmeIMO,file_ReadmeIMO_str);
  reset(freadmeIMO);
  {wyszukanie w pierwszych 3 wierszach roku}
  found:=FALSE;
  repeat
    i:=i+1;
    readln(freadmeIMO,line_str);
    line_str:=AnsiUpperCase(line_str);
    pos:=PosEx(year_str,line_str,1);
    if pos<>0 then
      found:=TRUE;
  until found or (i=3) or eof(freadmeIMO);
  if found then
    begin {w naglowku znaleziono year_str z linii komendy wywolania check1min}
    end {w naglowku znaleziono year_str z linii komendy wywolania check1min}
  else
    begin  {w naglowku NIE znaleziono year_str z linii komendy wywolania check1min}
      writeln(fraport,'   WARNING! There is not found ', year_str, ' in the header of readme.', IMO_str);
    end; {w naglowku NIE znaleziono year_str z linii komendy wywolania check1min}

  close(freadmeIMO);

  if ReadmeIMO_EOL<>1 then
    begin
      DeleteFile('tmp_check1min.tmp');
    end;
end; {Procedure Check_ReadmeIMO_Year_Header}


Procedure Check_ReadmeIMO_Colatitude;
var file_ReadmeIMO_str:string250;
    line_str:string250;
    temp1_str:string250;
    freadmeIMO:text;
    code:integer;
    found:boolean;
    pos:integer;
    colatitude:real; {co-latitude odczytane z readme.imo}

begin {Procedure Check_ReadmeIMO_Colatitude}
  if ReadmeIMO_EOL=1 then
    begin
      file_ReadmeIMO_str:=Dir_iaf_str+'\readme.'+IMO_str;
    end
  else
    begin
      Text_Any_System_to_Windows(Dir_iaf_str+'\readme.'+IMO_str,'tmp_check1min.tmp');
      file_ReadmeIMO_str:='tmp_check1min.tmp';
    end;

  AssignFile(freadmeIMO,file_ReadmeIMO_str);
  reset(freadmeIMO);
  {wyszukanie wiersza zawierajacego CO-LATITUDE
   ENG. searching for text 'CO-LATITUDE'}
  found:=FALSE;
  repeat
      readln(freadmeIMO,line_str);
      line_str:=AnsiUpperCase(line_str);
      pos:=PosEx('CO-LATITUDE',line_str,1);
      if pos<>0 then
        found:=TRUE;
  until found or eof(freadmeIMO);
  if found then
    begin {znaleziono CO-LATITUDE}
      temp1_str:=copy(line_str,length('CO-LATITUDE')+pos+1,length(line_str)-length('CO-LATITUDE'));
      {kasowanie piewszej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[1] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,1,1)
        end;
      {kasowanie ostatniej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[length(temp1_str)] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,length(temp1_str),1)
        end;
      {proba konwersji co-latitude do liczby
       ENG. attemt to convert co-latitude to numerical value}
      val(temp1_str,colatitude,code);
      if code=0 then
        begin
          {porównanie z W03}
          if abs(colatitude-Headers[1].W03/1000)>=0.001 then
            begin
              writeln(fraport,'   CO-LATITUDE in readme.imo = ',colatitude:8:4);
              writeln(fraport,'   CO-LATITUDE in IAF        = ',Headers[1].W03/1000:8:4,' degrees');
            end;
        end
      else
        begin
          writeln(fraport,'   WARNING! co-latitude is not correct number, should be in degrees');
        end;
    end {znaleziono CO-LATITUDE}
  else
    begin  {nie znaleziono CO-LATITUDE; ENG. not found CO-LATITUDE}
      writeln(fraport,'   WARNING! Not found string "CO-LATITUDE"');
    end; {nie znaleziono CO-LATITUDE; ENG. not found CO-LATITUDE}

  close(freadmeIMO);

  if ReadmeIMO_EOL<>1 then
    begin
      DeleteFile('tmp_check1min.tmp');
    end;
end; {Procedure Check_ReadmeIMO_Colatitude}


Procedure Check_ReadmeIMO_Longitude;
var file_ReadmeIMO_str:string250;
    line_str:string250;
    temp1_str:string250;
    freadmeIMO:text;
    code:integer;
    found:boolean;
    pos:integer;
    longitude:real; {longitude odczytane z readme.imo; ENG. longitude read from readme.imo}

begin {Procedure Check_ReadmeIMO_Longitude}
  if ReadmeIMO_EOL=1 then
    begin
      file_ReadmeIMO_str:=Dir_iaf_str+'\readme.'+IMO_str;
    end
  else
    begin
      Text_Any_System_to_Windows(Dir_iaf_str+'\readme.'+IMO_str,'tmp_check1min.tmp');
      file_ReadmeIMO_str:='tmp_check1min.tmp';
    end;

  AssignFile(freadmeIMO,file_ReadmeIMO_str);
  reset(freadmeIMO);
  {wyszukanie wiersza zawierajacego LONGITUDE;
   ENG. searching line which contains text LONGITUDE}
  found:=FALSE;
  repeat
      readln(freadmeIMO,line_str);
      line_str:=AnsiUpperCase(line_str);
      pos:=PosEx('LONGITUDE',line_str,1);
      if pos<>0 then
        found:=TRUE;
  until found or eof(freadmeIMO);
  if found then
    begin {znaleziono LONGITUDE}
      temp1_str:=copy(line_str,length('LONGITUDE')+pos+1,length(line_str)-length('LONGITUDE'));
      {kasowanie piewszej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[1] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,1,1)
        end;
      {kasowanie ostatniej nie-cyfry;
       ENG. erasing last non-digit character}
      while ((temp1_str<>'') and (not (temp1_str[length(temp1_str)] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,length(temp1_str),1)
        end;
      {proba konwersji longitude do liczby;
       ENG. attemt to convert longitude to numerical value}
      val(temp1_str,longitude,code);
      if code=0 then
        begin
          {porównanie z W04}
          if abs(longitude-Headers[1].W04/1000)>=0.001 then
            begin
              writeln(fraport,'   LONGITUDE in readme.imo = ',longitude:8:4);
              writeln(fraport,'   LONGITUDE in IAF        = ',Headers[1].W04/1000:8:4,' degrees');
              if abs(longitude-Headers[1].W04/1000)>=1.0 then
                writeln(fraport,'      LONGITUDE should be in degrees, 0..360, East');
            end;
        end
      else
        begin
          writeln(fraport,'   WARNING! longitude is not correct number, should be in degrees');
        end;
    end {znaleziono LONGITUDE}
  else
    begin  {nie znaleziono LONGITUDE}
      writeln(fraport,'   WARNING! Not found string "LONGITUDE"');
    end; {nie znaleziono LONGITUDE}

  close(freadmeIMO);

  if ReadmeIMO_EOL<>1 then
    begin
      DeleteFile('tmp_check1min.tmp');
    end;
end; {Procedure Check_ReadmeIMO_Longitude}


Procedure Check_ReadmeIMO_Elevation;
var file_ReadmeIMO_str:string250;
    line_str:string250;
    temp1_str:string250;
    freadmeIMO:text;
    code:integer;
    found:boolean;
    pos:integer;
    elevation:real; {elevation odczytane z readme.imo}

begin {Procedure Check_ReadmeIMO_Elevation}
  if ReadmeIMO_EOL=1 then
    begin
      file_ReadmeIMO_str:=Dir_iaf_str+'\readme.'+IMO_str;
    end
  else
    begin
      Text_Any_System_to_Windows(Dir_iaf_str+'\readme.'+IMO_str,'tmp_check1min.tmp');
      file_ReadmeIMO_str:='tmp_check1min.tmp';
    end;

  AssignFile(freadmeIMO,file_ReadmeIMO_str);
  reset(freadmeIMO);
  {wyszukanie wiersza zawierajacego ELEVATION}
  found:=FALSE;
  repeat
      readln(freadmeIMO,line_str);
      line_str:=AnsiUpperCase(line_str);
      pos:=PosEx('ELEVATION',line_str,1);
      if pos<>0 then
        found:=TRUE;
  until found or eof(freadmeIMO);
  if found then
    begin {znaleziono ELEVATION}
      temp1_str:=copy(line_str,length('ELEVATION')+pos+1,length(line_str)-length('ELEVATION'));
      {kasowanie piewszej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[1] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,1,1)
        end;
      {kasowanie ostatniej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[length(temp1_str)] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,length(temp1_str),1)
        end;
      {proba konwersji elevation do liczby}
      val(temp1_str,elevation,code);
      if code=0 then
        begin
          {porównanie z W04}
          if abs(elevation-Headers[1].W05/1)>=1.0 then
            begin
              writeln(fraport,'     ELEVATION in readme.imo = ',elevation:7:1);
              writeln(fraport,'     ELEVATION in IAF        = ',Headers[1].W05/1:7:1,' meters');
            end;
        end
      else
        begin
          writeln(fraport,'   WARNING! elevation is not correct number or another reason');
        end;
    end {znaleziono ELEVATION}
  else
    begin  {nie znaleziono ELEVATION}
      writeln(fraport,'   WARNING! Not found string "ELEVATION"');
    end; {nie znaleziono ELEVATION}

  close(freadmeIMO);

  if ReadmeIMO_EOL<>1 then
    begin
      DeleteFile('tmp_check1min.tmp');
    end;
end; {Procedure Check_ReadmeIMO_Elevation}


Procedure Check_ReadmeIMO_K9limit;
var file_ReadmeIMO_str:string250;
    line_str:string250;
    temp1_str:string250;
    freadmeIMO:text;
    code:integer;
    found:integer;
    pos:integer;
    position:integer;
    K9limit:real; {K9limit odczytane z readme.imo}

begin {Procedure Check_ReadmeIMO_K9limit}
  if ReadmeIMO_EOL=1 then
    begin
      file_ReadmeIMO_str:=Dir_iaf_str+'\readme.'+IMO_str;
    end
  else
    begin
      Text_Any_System_to_Windows(Dir_iaf_str+'\readme.'+IMO_str,'tmp_check1min.tmp');
      file_ReadmeIMO_str:='tmp_check1min.tmp';
    end;

  AssignFile(freadmeIMO,file_ReadmeIMO_str);
  reset(freadmeIMO);
  {wyszukanie wiersza zawierajacego K9limit}
  found:=0;
  repeat
      readln(freadmeIMO,line_str);
      line_str:=AnsiUpperCase(line_str);
      pos:=PosEx('K9-LIMIT',line_str,1);
      if pos<>0 then begin found:=1; position:=pos end;
      pos:=PosEx('K9 - LIMIT',line_str,1);
      if pos<>0 then begin found:=2; position:=pos end;
      pos:=PosEx('K9 LIMIT',line_str,1);
      if pos<>0 then begin found:=3; position:=pos end;
      pos:=PosEx('K=9 LIMIT',line_str,1);
      if pos<>0 then begin found:=4; position:=pos end;
      pos:=PosEx('K-9 LIMIT',line_str,1);
      if pos<>0 then begin found:=5; position:=pos end;
  until ((found<>0) or (eof(freadmeIMO)));
  if found<>0 then
    begin {znaleziono K9limit}
      case found of
        1 : temp1_str:=copy(line_str,length('K9-LIMIT')+position+1,length(line_str)-length('K9-LIMIT'));
        2 : temp1_str:=copy(line_str,length('K9 - LIMIT')+position+1,length(line_str)-length('K9 - LIMIT'));
        3 : temp1_str:=copy(line_str,length('K9 LIMIT')+position+1,length(line_str)-length('K9 LIMIT'));
        4 : temp1_str:=copy(line_str,length('K=9 LIMIT')+position+1,length(line_str)-length('K=9 LIMIT'));
        5 : temp1_str:=copy(line_str,length('K-9 LIMIT')+position+1,length(line_str)-length('K-9 LIMIT'));
      end;
      {kasowanie piewszej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[1] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,1,1)
        end;
      {kasowanie ostatniej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[length(temp1_str)] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,length(temp1_str),1)
        end;
      {proba konwersji K9limit do liczby}
      val(temp1_str,K9limit,code);
      if code=0 then
        begin
          {porównanie z W04}
          if abs(K9limit-Headers[1].W11/1)>0.0 then
            begin
              writeln(fraport,'     K9-limit in readme.imo = ',K9limit:7:1,' nT');
              writeln(fraport,'     K9-limit in IAF        = ',Headers[1].W11/1:7:1,' nT');
            end;
        end
      else
        begin
          writeln(fraport,'   WARNING! K9-limit is not correct number');
        end;
    end {znaleziono K9limit}
  else
    begin  {nie znaleziono K9limit}
      writeln(fraport,'   WARNING! Not found string K9-LIMIT or similar');
    end; {nie znaleziono K9limit}

  close(freadmeIMO);

  if ReadmeIMO_EOL<>1 then
    begin
      DeleteFile('tmp_check1min.tmp');
    end;
end; {Procedure Check_ReadmeIMO_K9limit}


Procedure Comparison_colatitude_IAF_yearmean;
var file_YearmeanIMO_str:string250;
    line_str:string250;
    temp1_str:string250;
    fyearmeanIMO:text;
    code:integer;
    found:boolean;
    pos:integer;
    colatitude:real; {COLATITUDE odczytane z yearmean.imo}

begin {Procedure Comparison_colatitude_IAF_yearmean}
  if yearmean_EOL=1 then
    begin
      file_YearmeanIMO_str:=Dir_iaf_str+'\yearmean.'+IMO_str;
    end
  else
    begin
      Text_Any_System_to_Windows(Dir_iaf_str+'\yearmean.'+IMO_str,'tmp_check1min.tmp');
      file_YearmeanIMO_str:='tmp_check1min.tmp';
    end;

  AssignFile(fyearmeanIMO,file_YearmeanIMO_str);
  reset(fyearmeanIMO);
  {wyszukanie wiersza zawierajacego COLATITUDE}
  found:=FALSE;
  repeat
      readln(fyearmeanIMO,line_str);
      line_str:=AnsiUpperCase(line_str);
      pos:=PosEx('COLATITUDE',line_str,1);
      if pos<>0 then
        found:=TRUE;
  until found or eof(fyearmeanIMO);
  if found then
    begin {znaleziono COLATITUDE}
      temp1_str:=copy(line_str,length('COLATITUDE')+pos+1,length(line_str)-length('COLATITUDE'));
      {kasowanie piewszej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[1] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,1,1)
        end;

      {zgrubne obciêcie koñca stringu ???}
      temp1_str:=copy(temp1_str,1,11);

      {kasowanie ostatniej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[length(temp1_str)] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,length(temp1_str),1)
        end;

      {proba konwersji colatitude do liczby}
      val(temp1_str,colatitude,code);
      if code=0 then
        begin
          {porównanie z W03}
          if abs(colatitude-Headers[1].W03/1000)>=0.001 then
            begin
              writeln(fraport,'   Warning!');
              writeln(fraport,'   COLATITUDE in yearmean.imo = ',colatitude:8:3);
              writeln(fraport,'   COLATITUDE in IAF          = ',Headers[1].W03/1000:8:3);
              writeln(fraport);
            end;
        end
      else
        begin
          writeln(fraport,'   WARNING! COLATITUDE is not correct number in yearmean.imo, should be in degrees');
        end;
    end {znaleziono COLATITUDE}
  else
    begin  {nie znaleziono COLATITUDE}
      writeln(fraport,'   WARNING! Not found string "COLATITUDE" in yearmean.imo file');
    end; {nie znaleziono COLATITUDE}

  close(fyearmeanIMO);

  if yearmean_EOL<>1 then
    begin
      DeleteFile('tmp_check1min.tmp');
    end;
end; {Procedure Comparison_colatitude_IAF_yearmean}


Procedure Comparison_longitude_IAF_yearmean;
var file_YearmeanIMO_str:string250;
    line_str:string250;
    temp1_str:string250;
    fyearmeanIMO:text;
    code:integer;
    found:boolean;
    pos:integer;
    longitude:real; {LONGITUDE odczytane z yearmean.imo}

begin {Procedure Comparison_longitude_IAF_yearmean}
  if yearmean_EOL=1 then
    begin
      file_YearmeanIMO_str:=Dir_iaf_str+'\yearmean.'+IMO_str;
    end
  else
    begin
      Text_Any_System_to_Windows(Dir_iaf_str+'\yearmean.'+IMO_str,'tmp_check1min.tmp');
      file_YearmeanIMO_str:='tmp_check1min.tmp';
    end;

  AssignFile(fyearmeanIMO,file_YearmeanIMO_str);
  reset(fyearmeanIMO);
  {wyszukanie wiersza zawierajacego LONGITUDE}
  found:=FALSE;
  repeat
      readln(fyearmeanIMO,line_str);
      line_str:=AnsiUpperCase(line_str);
      pos:=PosEx('LONGITUDE',line_str,1);
      if pos<>0 then
        found:=TRUE;
  until found or eof(fyearmeanIMO);
  if found then
    begin {znaleziono LONGITUDE}
      temp1_str:=copy(line_str,length('LONGITUDE')+pos+1,length(line_str)-length('LONGITUDE'));
      {kasowanie piewszej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[1] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,1,1)
        end;

      {zgrubne obciêcie koñca stringu ???}
      temp1_str:=copy(temp1_str,1,11);

      {kasowanie ostatniej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[length(temp1_str)] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,length(temp1_str),1)
        end;

      {proba konwersji longitude do liczby}
      val(temp1_str,longitude,code);
      if code=0 then
        begin
          {porównanie z W04}
          if abs(longitude-Headers[1].W04/1000)>=0.001 then
            begin
              writeln(fraport,'   Warning!');
              writeln(fraport,'   LONGITUDE in yearmean.imo = ',longitude:8:3);
              writeln(fraport,'   LONGITUDE in IAF          = ',Headers[1].W04/1000:8:3);
              writeln(fraport);
            end;
        end
      else
        begin
          writeln(fraport,'   WARNING! LONGITUDE is not correct number in yearmean.imo, should be in degrees');
        end;
    end {znaleziono LONGTITUDE}
  else
    begin  {nie znaleziono LONGITUDE}
      writeln(fraport,'   WARNING! Not found string "LONGITUDE" in yearmean.imo file');
    end; {nie znaleziono LONGITUDE}

  close(fyearmeanIMO);

  if yearmean_EOL<>1 then
    begin
      DeleteFile('tmp_check1min.tmp');
    end;
end; {Procedure Comparison_longitude_IAF_yearmean}



Procedure Comparison_elevation_IAF_yearmean;
var file_YearmeanIMO_str:string250;
    line_str:string250;
    temp1_str:string250;
    fyearmeanIMO:text;
    code:integer;
    found:boolean;
    pos:integer;
    elevation:real; {ELEVATION odczytane z yearmean.imo}

begin {Procedure Comparison_elevation_IAF_yearmean}
  if yearmean_EOL=1 then
    begin
      file_YearmeanIMO_str:=Dir_iaf_str+'\yearmean.'+IMO_str;
    end
  else
    begin
      Text_Any_System_to_Windows(Dir_iaf_str+'\yearmean.'+IMO_str,'tmp_check1min.tmp');
      file_YearmeanIMO_str:='tmp_check1min.tmp';
    end;

  AssignFile(fyearmeanIMO,file_YearmeanIMO_str);
  reset(fyearmeanIMO);
  {wyszukanie wiersza zawierajacego ELEVATION}
  found:=FALSE;
  repeat
      readln(fyearmeanIMO,line_str);
      line_str:=AnsiUpperCase(line_str);
      pos:=PosEx('ELEVATION',line_str,1);
      if pos<>0 then
        found:=TRUE;
  until found or eof(fyearmeanIMO);
  if found then
    begin {znaleziono ELEVATION}
      temp1_str:=copy(line_str,length('ELEVATION')+pos+1,length(line_str)-length('ELEVATION'));
      {kasowanie piewszej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[1] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,1,1)
        end;

      {zgrubne obciêcie koñca stringu ???}
      temp1_str:=copy(temp1_str,1,11);

      {kasowanie ostatniej nie-cyfry}
      while ((temp1_str<>'') and (not (temp1_str[length(temp1_str)] in ['0','1','2','3','4','5','6','7','8','9']))) do
        begin
          delete(temp1_str,length(temp1_str),1)
        end;

      {proba konwersji elevation do liczby}
      val(temp1_str,elevation,code);
      if code=0 then
        begin
          {porównanie z W05}
          if abs(elevation-Headers[1].W05/1)>=1 then
            begin
              writeln(fraport,'   Warning!');
              writeln(fraport,'   ELEVATION in yearmean.imo = ',elevation:6:0);
              writeln(fraport,'   ELEVATION in IAF          = ',Headers[1].W05:6);
              writeln(fraport);
            end;
        end
      else
        begin
          writeln(fraport,'   WARNING! ELEVATION is not correct number in yearmean.imo');
        end;
    end {znaleziono ELEVATION}
  else
    begin  {nie znaleziono ELEVATION}
      writeln(fraport,'   WARNING! Not found string "ELEVATION" in yearmean.imo file');
    end; {nie znaleziono ELEVATION}

  close(fyearmeanIMO);

  if yearmean_EOL<>1 then
    begin
      DeleteFile('tmp_check1min.tmp');
    end;
end; {Procedure Comparison_elevation_IAF_yearmean}




Procedure Appendix;
begin {Procedure Appendix}
  writeln(fraport,'1. Hourly mean values:');
  writeln(fraport,'    - Arithmetic average of the 1-minute data');
  writeln(fraport,'    - Centered on the centre of the hour which is defined by minutes 00-59 of that hour');
  writeln(fraport,'2. Daily mean values:');
  writeln(fraport,'    - Arithmetic average of the 1-minute data');
  writeln(fraport,'    - Centered on the centre of the day defined by 00:00-23:59');
  writeln(fraport,'3. Annual mean values:');
  writeln(fraport,'    - Arithmetic average of the 1-minute data');
  writeln(fraport,'    - Centered on the centre of the year defined by the dates between 01 Jan 00:00 – 31 Dec 23:59');
  writeln(fraport,'4. Missing values');
  writeln(fraport,'      In case of missing 1-minute data, hourly, daily, and annual mean values');
  writeln(fraport,'      are processed only if at least 90% of the considered 1-minute data does exist');
end; {Procedure Appendix}


begin {program}
  X_yearmean:=999999.0;
  Y_yearmean:=999999.0;
  Z_yearmean:=999999.0;
  DailyMeans_found_problems:=0;
  HourlyMeans_found_problems:=0;

  if ParamCount<>4 then
    begin {zla ilosc parametrow}
      writeln;
      writeln('                     check1min     ver. 1.71, Belsk 2021-06-23');
      writeln;
      writeln(' The program inspects Intermagnet Definitive files prepared for CD/DVD/USB/IRDS one-minute compilation');
      writeln;
      writeln('The program should be called with 4 arguments');
      writeln(' Example:');
      writeln('    check1min D:\MAG2014\HUA HUA 2014 REPORT.TXT');
      writeln(' In this example:');
      writeln('    D:\MAG2014\HUA        directory containing files of HUA for DVD2014');
      writeln('                          (12 IAF files, YEARMEAN.HUA, HUA2014.BLV, README.HUA)');
      writeln('    HUA                   IAGA code of given IMO');
      writeln('    2014                  year');
      writeln('    REPORT.TXT            the report file (text file)');
      writeln;
      writeln;
      writeln;
      writeln(' Press ESC');
      repeat
        ch_esc:=ReadKey;
      until ch_esc=#27;
      halt;

    end {zla ilosc parametrow}
  else
    begin {dobra ilosc parametrow}
      Dir_iaf_str:=ParamStr(1);
      Dir_iaf_str:=LowerCase(Dir_iaf_str);
      dir_iaf_str:=ExpandFileName(dir_iaf_str);
      if not Exist_Dir(dir_iaf_str) then
        begin
          writeln;
          writeln('There is missing directory',dir_iaf_str);
          writeln('Continuation impossible');
          
          writeln(fraport);
          writeln(fraport,'There is missing directory',dir_iaf_str);
          writeln(fraport,'Continuation impossible');
          {
          writeln(' Press ESC');
          repeat
            ch_esc:=ReadKey;
          until ch_esc=#27;
          }
          CloseFile(fraport);
          halt
        end;
      IMO_str:=ParamStr(2);
      IMO_str:=LowerCase(IMO_str);
      if length(IMO_str)<>3 then
        begin
          writeln;
          Writeln('Something wrong in 2-nd parameter - length of IMO code <> 3 chars');
          writeln('Continuation impossible');

          writeln(fraport);
          Writeln(fraport,'Something wrong in 2-nd parameter - length of IMO code <> 3 chars');
          writeln(fraport,'Continuation impossible');
          {
          writeln(' Press ESC');
          repeat
            ch_esc:=ReadKey;
          until ch_esc=#27;
          }
          CloseFile(fraport);
          halt;
        end;
      year_str:=ParamStr(3);
      year_str:=LowerCase(year_str);
      Val(year_str,year,code);
      if ((code<>0) or (year<1980) or (year>=2040)) then
        begin
          writeln;
          Writeln('Something wrong in 3-rd parameter (year)');
          writeln('Continuation impossible');

          writeln(fraport);
          Writeln(fraport,'Something wrong in 3-rd parameter (year)');
          writeln(fraport,'Continuation impossible');
          {
          writeln(' Press ESC');
          repeat
            ch_esc:=ReadKey;
          until ch_esc=#27;
          }
          CloseFile(fraport);
          halt;
        end;
      if (frac(year/4)=0.0) then
        Max_day:=366
      else
        Max_day:=365;
      Raport_str:=ParamStr(4);
      Raport_str:=LowerCase(Raport_str);
      Raport_str:=ExpandFileName(Raport_str);
      AssignFile(fraport,Raport_str);
      rewrite(fraport);
      temp1_str:='check1min '+ParamStr(1)+' '+ParamStr(2)+' '+ParamStr(3)+' '+ParamStr(4);
      writeln(fraport,temp1_str);
      temp1_str:='check1min ver. 1.71 for IMBOT, June 2021, Belsk';
      writeln(fraport,temp1_str);
      writeln(fraport);
      temp1_str:='Inspection of dataset prepared for CD/DVD/USB/IRDS compilation          Date&Time: ';
      temp1_str:=temp1_str+DateToStr(Date)+' '+TimeToStr(Time);
      writeln(fraport,temp1_str);
      writeln(fraport);

      Czy_sa_IAF;
      writeln(fraport,'======== Checking presence readme.imo yearmean.imo imoyyyy.blv =======');
      Czy_jest_yearmean;
      Czy_jest_BLV;
      Czy_jest_ReadmeIMO;
      writeln(fraport);

      writeln(fraport,'======= Checking chars at the end of the line in text files ==========');
      Message_if_text_no_Windows;

      if yearmean_file_present then
          Read_XYZF_from_yearmean;
      if BLV_present then
          Read_HF_from_BLV;

      writeln(fraport,'============== Checking W01..W16 headers in IAF files ================');
      if IAF_present then
        begin
          Read_IAF_headers;
          Read_XYZG_minute;
          Read_XYZG_hour;
          Read_XYZG_day;
          Read_Kindices;
          Check_Headers;
          Calculations_yearly_daily_hourly_means;
        end;
      writeln(fraport);
      writeln(fraport,'================ YEARMEAN file versus IAF files ======================');
      writeln(fraport); writeln(fraport,'COMPARISON '+year_str+' YEARMEANS reported in yearmean.'+IMO_str+' (All days) and calculated from '+IMO_str+copy(year_str,3,2)+'???.bin');
      if IAF_present and yearmean_file_present then
        begin
          ComparisonYearly_IAF_yearmean;
          Comparison_colatitude_IAF_yearmean;
          Comparison_longitude_IAF_yearmean;
          Comparison_elevation_IAF_yearmean;
        end
      else
        begin
          temp1_str:='     WARNING: '+IMO_str+copy(year_str,3,2)+'???.bin or yearmean.'+IMO_str+' is missing - comparison impossible';
          writeln(fraport,temp1_str);
        end;
      writeln(fraport);

      writeln(fraport,'================ Checking BLV file ===================================');
      if BLV_present and IAF_present then
        begin
          Check_BLV;
        end;

      writeln(fraport,'============== Checking K-indices in IAF files =======================');
      if IAF_present then
        begin
          Check_K_indices;
        end;

      writeln(fraport,'================== Checking Readme.IMO file ==========================');
      if ReadmeIMO_present and IAF_present then
        begin
          Check_ReadmeIMO_Year_Header;
          Check_ReadmeIMO_Colatitude;
          Check_ReadmeIMO_Longitude;
          Check_ReadmeIMO_Elevation;
          Check_ReadmeIMO_K9limit;
        end;
      writeln(fraport);
      writeln(fraport);
      writeln(fraport,'====== Checking the calculation daily and hourly means ===============');
      Check_Daily_mean_reported2;
      Check_Hourly_mean_reported2;
      writeln(fraport);
      if yearmean_file_present then
        Call_ymchk;
      writeln(fraport);
      if ((DailyMeans_found_problems>0) or (HourlyMeans_found_problems>0)) then
        begin
          writeln(fraport,'=== APPENDIX - IAGA rules for hourly, daily and annual mean values calculation ===');
          Appendix;
        end;
      CloseFile(fraport);
      writeln;
      writeln('Done. The results are in the text file: ',raport_str);
      Delay(1000);
    end; {dobra ilosc parametrow}
end. {program}

{
K-NUMBERS
K-indices:          not produced
None
FMI-method
ASm
Kasm
not measured
Handscaled
AS method
MNOC-method
USGS
FMI method
Computer-assisted scaling
Handscaled
Hand scaled
LRNS-method
AS method
Computer assisted hand-scaled
Computer derived (Finish method)
HS(Hand scale)-method    LRNS-method as reference
Sr variation assumed negligibly small
Finish method
Polish method
K-NUMBERS    : K9-limit is 300 nT, calculated by KASM
K-indices:          Provided in a separate file on this cd-
                    rom and calculated by the IAGA Polish 
                    algorithm



K-indices:          not produced


K9-limit
K9-LIMIT     : 300 nT
K9-LIMIT:        300 nT
K9 - limit    : 460 nT
K9 limit      450 nT
K9 limit:     500 nT
K9 - limit    : 1800 nT
K=9 LIMIT    : 300 nT
K9-LIMIT:                                 (KDU)
K-LIMIT     : 500 nT
K-9 LIMIT    : 350 nT
K9 limit:     700 nT
brak takiej linni w ABK,ASC,HBK
}

