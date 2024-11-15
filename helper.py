import random

from pathlib import Path
from hashlib import md5
from docling.document_converter import DocumentConverter
from docling.datamodel.document import ConversionResult
import pandas as pd

def create_uuid(data: str = None) -> int:
    if data is None:
        return random.randrange(1 << 30, 1 << 31 )

    return int(data.encode("utf-8").hex(), 16) % (10**10)

def get_id(data: str) -> str:
    sum = get_hashsum(data)
    return create_uuid(sum)

def get_hashsum(data: str) -> str: 
    if data is None:
        return create_uuid()
    return md5(data.encode('utf-8')).hexdigest()

def load_excel(filename: Path, sheet: str = 'Sheet1') :
    data_frame = pd.read_excel(io=filename, sheet_name=sheet)
    return data_frame.to_dict(orient='records')

def read_template(filename: str) -> str: 
    with open(f"templates/{filename}", 'r') as f :
        return f.read()
    
def extract_table_from_img(source: str, lang: str) -> pd.DataFrame:
    """
    Extract tables from a PDF file.
    """  
    converter = DocumentConverter()
    result: ConversionResult = converter.convert(source)
    for table_ix, table in enumerate(result.document.tables):
        table_df: pd.DataFrame = table.export_to_dataframe()
        return table_df
        
