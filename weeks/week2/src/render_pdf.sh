#!/bin/sh
# Render the report to PDF and compress it below the portal's 2 MB upload cap.
#
# The .docx keeps 256-colour PNGs, which is lossless enough at print size. The
# PDF is re-encoded as JPEG at 200 dpi: text stays vector, figures stay above
# 200 dpi, and the file falls from about 2.5 MB to 1.8 MB.
set -eu
cd "$(dirname "$0")/.."

soffice --headless --convert-to pdf --outdir reports \
  reports/Week2_EDA_and_Visualization.docx

temporary=$(mktemp /tmp/week2-report.XXXXXX)
trap 'rm -f "$temporary"' EXIT

gs -q -sDEVICE=pdfwrite -dCompatibilityLevel=1.6 -dNOPAUSE -dBATCH \
  -dAutoRotatePages=/None \
  -dDownsampleColorImages=true -dColorImageResolution=200 \
  -dColorImageDownsampleType=/Average \
  -dColorImageFilter=/DCTEncode -dAutoFilterColorImages=false \
  -dEncodeColorImages=true -dJPEGQ=88 \
  -sOutputFile="$temporary" reports/Week2_EDA_and_Visualization.pdf

mv "$temporary" reports/Week2_EDA_and_Visualization.pdf
chmod 644 reports/Week2_EDA_and_Visualization.pdf
trap - EXIT

ls -lh reports/Week2_EDA_and_Visualization.docx reports/Week2_EDA_and_Visualization.pdf
