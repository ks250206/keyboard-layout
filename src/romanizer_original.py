SIMPLE={}
for onset, row in [('', 'あいうえお'),('k','かきくけこ'),('s','さしすせそ'),('t','たちつてと'),('n','なにぬねの'),('h','はひふへほ'),('m','まみむめも'),('y','や　ゆ　よ'),('r','らりるれろ'),('w','わ　　　を'),('g','がぎぐげご'),('z','ざじずぜぞ'),('d','だぢづでど'),('b','ばびぶべぼ'),('p','ぱぴぷぺぽ')]:
 for vow,kana in zip('aiueo',row):
  if kana!='　': SIMPLE[kana]=onset+vow
SIMPLE.update({'ん':'n','ゔ':'vu','ゐ':'wi','ゑ':'we','ぁ':'xa','ぃ':'xi','ぅ':'xu','ぇ':'xe','ぉ':'xo','ゃ':'xya','ゅ':'xyu','ょ':'xyo','っ':'xtu','を':'wo'})
# Explicit small-y combos to override naive composition (incl. short j)
YCO={
 'き':'ky','ぎ':'gy','し':'sy','じ':'j','ち':'ty','ぢ':'dy','に':'ny',
 'ひ':'hy','び':'by','ぴ':'py','み':'my','り':'ry'
}
FORCE={'ふぁ':'fa','ふぃ':'fi','ふぇ':'fe','ふぉ':'fo','てぃ':'thi','でぃ':'dhi'}

def romanize(reading):
 result=[];i=0
 while i<len(reading):
  ch=reading[i]
  if ch=='、':result.append(',');i+=1;continue
  if ch=='。':result.append('.');i+=1;continue
  if ch=='ー':result.append('-');i+=1;continue
  if ch in ' \t\r\n':i+=1;continue
  if ch=='ん':
   # Explicit nn for vowel, y, n following kana; terminal n otherwise (IME strategy).
   next_ch=reading[i+1] if i+1<len(reading) else ''
   if next_ch in 'あいうえおやゆよなにぬねの':result.append('nn')
   else:result.append('n')
   i+=1;continue
  if ch=='っ' and i+1<len(reading):
   next_part=romanize(reading[i+1:i+3])
   if next_part and next_part[0] not in 'aiueo,.-':
    result.append(next_part[0]);i+=1;continue
  duo=reading[i:i+2]
  if duo in FORCE:
   result.append(FORCE[duo]);i+=2;continue
  if len(duo)==2 and duo[1] in 'ゃゅょ' and ch in YCO:
   result.append(YCO[ch]+{'ゃ':'a','ゅ':'u','ょ':'o'}[duo[1]]);i+=2;continue
  if ch in SIMPLE:result.append(SIMPLE[ch]);i+=1;continue
  raise ValueError(f'unrecognised kana {repr(ch)}, context {reading[max(0,i-6):i+6]}')
 return ''.join(result)
