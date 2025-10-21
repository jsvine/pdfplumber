import os
import unittest
import pytest
import pdfplumber
HERE = os.path.abspath(os.path.dirname(__file__))

class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/pdffill-demo.pdf")
        self.pdf = pdfplumber.open(path)

    @classmethod
    def teardown_class(self):
        self.pdf.close()
        
    def test_lacking_outer_borders(self):
            # See https://github.com/jsvine/pdfplumber/issues/1325    
            
        path = os.path.join(HERE, "pdfs/issue-1325.pdf")
        with pdfplumber.open(path) as pdf:
            pdf.pages[1].to_image(150).debug_tablefinder(table_settings={}).show()
        