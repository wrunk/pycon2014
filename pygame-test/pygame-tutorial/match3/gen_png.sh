export LANG=C

INKSCAPE=/Applications/Inkscape.app/Contents/Resources/bin/inkscape
for i in *.svg;
do
  ${INKSCAPE} $i -w 24 -e data/`echo $i | sed -e 's/.svg/-24.png/'`;
  ${INKSCAPE} $i -w 36 -e data/`echo $i | sed -e 's/.svg/-36.png/'`;
  ${INKSCAPE} $i -w 48 -e data/`echo $i | sed -e 's/.svg/-48.png/'`;
  ${INKSCAPE} $i -w 64 -e data/`echo $i | sed -e 's/.svg/-64.png/'`;
  ${INKSCAPE} $i -w 72 -e data/`echo $i | sed -e 's/.svg/-72.png/'`;
  ${INKSCAPE} $i -w 96 -e data/`echo $i | sed -e 's/.svg/-96.png/'`;
  ${INKSCAPE} $i -w 128 -e data/`echo $i | sed -e 's/.svg/-128.png/'`;
done

${INKSCAPE} android-icon.svg -w 48 -e android-icon.png
${INKSCAPE} android-presplash -w 128 -e android-presplash.png
convert android-presplash.png android-presplash.jpg
