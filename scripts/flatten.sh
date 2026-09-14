find . -mindepth 2 -type f \( -name "*.sh" -o -name "*.py" \) -print0 | while read -r -d '' file; do
  base=$(basename "$file")
  if [ -f "./$base" ]; then
    i=1
    while [ -f "./${base%.*}_$i.${base##*.}" ]; do
      i=$((i+1))
    done
    mv "$file" "./${base%.*}_$i.${base##*.}"
  else
    mv "$file" "./$base"
  fi
done
