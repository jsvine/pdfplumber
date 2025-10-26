import os
import unittest
import pytest
import pdfplumber
import json

HERE = os.path.abspath(os.path.dirname(__file__))

class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/issue-1325.pdf")
        self.pdf = pdfplumber.open(path)

    @classmethod
    def teardown_class(self):
        self.pdf.close()
        
    def test_lacking_outer_borders(self):
            # See https://github.com/jsvine/pdfplumber/issues/1325             
        path = os.path.join(HERE, "pdfs/issue-1325.pdf")
        with pdfplumber.open(path) as pdf:
            p1 = pdf.pages[1]
            p1 = p1.within_bbox((30, 295, p1.width-30, p1.height-60)) 
            
            extract = p1.extract_table(table_settings={})
                
                    
            assert extract[1] == ["kognitive\nLernvoraussetzungen","motivationale\nLernvoraussetzungen","emotionale\nLernvoraussetzungen", "inhaltliche\Bedingungen"]
            
        