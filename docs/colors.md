# Colors

In the PDF specification, as well as in `pdfplumber`, most graphical objects can have two color attributes:

- `stroking_color`: The color of the object's outline
- `non_stroking_color`: The color of the object's interior, or "fill"

In the PDF specification, colors have both a "color space" and a "color value".

## Color Spaces

Valid color spaces are grouped into three categories:

- Device color spaces
    - `DeviceGray`
    - `DeviceRGB`
    - `DeviceCMYK`
- CIE-based color spaces
    - `CalGray`
    - `CalRGB`
    - `Lab`
    - `ICCBased`
- Special color spaces
    - `Indexed`
    - `Pattern`
    - `Separation`
    - `DeviceN`

To read more about the differences between those color spaces, see section 4.5 [here](https://ghostscript.com/~robin/pdf_reference17.pdf).

`pdfplumber` aims to expose those color spaces as `scs` (stroking color space) and `ncs` (non-stroking color space), represented as a __string__.

__Caveat__: The only information `pdfplumber` can __currently__ expose is the non-stroking color space for `char` objects. The rest (stroking color space for `char` objects and either color space for the other types of objects) will require a pull request to `pdfminer.six`.

## Color Values

The color value determines *what specific color* in the color space should be used. With the exception of the "special color spaces," these color values are specified as a series of numbers. For `DeviceRGB`, for example, the color values are three numbers, representing the intensities of red, green, and blue.

In `pdfplumber`, those color values are exposed as `stroking_color` and `non_stroking_color`, represented as a __tuple of numbers__.

The pattern specified by the `Pattern` color space is exposed via the `non_stroking_pattern` and `stroking_pattern` attributes.
