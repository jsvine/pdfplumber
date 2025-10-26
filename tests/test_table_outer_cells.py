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

                                      
            # Used to visualise the output of the TableFinder  
            corners = [[42.5195, 301.942], [42.5195, 326.44200000000006], [42.5195, 389.812], [42.5195, 443.27200000000005], [42.5195, 486.821], [42.5195, 540.2809000000001], [390.68600000000004, 301.942], [390.68600000000004, 326.44200000000006], [390.68600000000004, 389.812], [390.68600000000004, 443.27200000000005], [390.68600000000004, 486.821], [390.68600000000004, 540.2809000000001]]
            img = p1.to_image(1200).debug_tablefinder(table_settings={})

            for corner in corners:
                img.draw_circle((corner[0], corner[1]), fill=(255,0,0, 30), radius=3, stroke=(255, 0, 0, 255))
             
            edges = [
                        {'x0': 42.5195, 'y0': 540.2809000000001, 'x1': 42.5195, 'y1': 301.942, 'width': 0.0, 'height': 238.33890000000008, 'pts': [(42.5195, 301.942), (129.561, 301.942)], 'linewidth': 4.95, 'stroke': True, 'fill': False, 'evenodd': False, 'stroking_color': (0.0, 0.0, 0.0), 'non_stroking_color': (0.0, 0.0, 0.0), 'mcid': None, 'tag': None, 'object_type': 'line', 'page_number': 2, 'path': [('m', (42.5195, 301.942)), ('l', (129.561, 301.942))], 'dash': None, 'top': 301.942, 'bottom': 540.2809000000001, 'doctop': 1092.808, 'orientation': 'v', 'points': [(42.5195, 540.2809000000001), (42.5195, 301.942)], 'SPECIAL': True},
                        {'x0': 390.68600000000004, 'y0': 540.2809000000001, 'x1': 390.68600000000004, 'y1': 301.942, 'width': 0.0, 'height': 238.33890000000008, 'pts': [(42.5195, 301.942), (129.561, 301.942)], 'linewidth': 4.95, 'stroke': True, 'fill': False, 'evenodd': False, 'stroking_color': (0.0, 0.0, 0.0), 'non_stroking_color': (0.0, 0.0, 0.0), 'mcid': None, 'tag': None, 'object_type': 'line', 'page_number': 2, 'path': [('m', (42.5195, 301.942)), ('l', (129.561, 301.942))], 'dash': None, 'top': 301.942, 'bottom': 540.2809000000001, 'doctop': 1092.808, 'orientation': 'v', 'points': [(390.68600000000004, 540.2809000000001), (390.68600000000004, 301.942)], 'SPECIAL': True}
                    ]
            
            for edge in edges:
                img.draw_line(edge["points"], stroke_width=5)
            img.show()
            
            extract = p1.extract_table(table_settings={})
                
            with open("output.json", "w") as F: # TODO remove all this before publishing
                json.dump(extract, F, indent=4)
                
                if extract[1] == ["kognitive\nLernvoraussetzungen","motivationale\nLernvoraussetzungen","emotionale\nLernvoraussetzungen", "inhaltliche\Bedingungen"]:
                    F.write("\nHeaders DO work")
                else:
                    F.write("\nHeaders DO NOT work")
                    
            assert extract[1] == ["kognitive\nLernvoraussetzungen","motivationale\nLernvoraussetzungen","emotionale\nLernvoraussetzungen", "inhaltliche\Bedingungen"]
            
            #F.write(p1.extract_text())
            #p1.extract_table(table_settings={})          
            
        