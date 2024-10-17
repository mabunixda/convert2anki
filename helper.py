import random

from pathlib import Path
from hashlib import md5
import cv2
import pytesseract
import pandas as pd

def create_uuid(data: str = None) -> int:
    if data is None:
        return random.randrange(1 << 30, 1 << 31 )

    return int(data.encode("utf-8").hex(), 16) % (10**10)

def get_hashsum(data: str) -> str: 
    return md5(data.encode('utf-8')).hexdigest()

def load_excel(filename: Path, sheet: str = 'Sheet1') :
    print(f"Loading {filename}")
    data_frame = pd.read_excel(io=filename, sheet_name=sheet)
    return data_frame.to_dict(orient='records')

def read_template(filename: str) -> str: 
    with open(f"templates/{filename}", 'r') as f :
        return f.read()
    
def extract_table_from_img(image: str) -> pd.DataFrame:
    """
    Extract tables from a PDF file.
    """  
    # Convert PIL Image to numpy array
    
    img = cv2.imread(image)
    img = cv2.resize(img, (int(img.shape[1] + (img.shape[1] * .1)),
                       int(img.shape[0] + (img.shape[0] * .25))),
                 interpolation=cv2.INTER_AREA)

    img_rgb = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)

    # https://stackoverflow.com/questions/61418907/how-to-convert-or-extract-a-table-from-an-image-using-tesseract
    custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1x1,tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-:.$%./@& *"'
    d = pytesseract.image_to_data(img_rgb, config=custom_config, output_type=pytesseract.Output.DICT)
    df = pd.DataFrame(d)

    # clean up blanks
    df1 = df[(df.conf != '-1') & (df.text != ' ') & (df.text != '')]
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)

    # sort blocks vertically
    sorted_blocks = df1.groupby('block_num').first().sort_values('top').index.tolist()
    output = ""
    for block in sorted_blocks:
        curr = df1[df1['block_num'] == block]
        sel = curr[curr.text.str.len() > 3]
        # sel = curr
        char_w = (sel.width / sel.text.str.len()).mean()
        prev_par, prev_line, prev_left = 0, 0, 0
        text = ''
        for ix, ln in curr.iterrows():
            # add new line when necessary
            if prev_par != ln['par_num']:
                text += '\n'
                prev_par = ln['par_num']
                prev_line = ln['line_num']
                prev_left = 0
            elif prev_line != ln['line_num']:
                text += '\n'
                prev_line = ln['line_num']
                prev_left = 0

            added = 0  # num of spaces that should be added
            if ln['left'] / char_w > prev_left + 1:
                added = int((ln['left']) / char_w) - prev_left
                text += ' ' * added
            text += ln['text'] + ' '
            prev_left += len(ln['text']) + added + 1
        text += '\n'
        output += text

    return output