# Third-Party Notices

This project uses third-party open-source software. The primary code of
FarmerVerify AI is released under the MIT License (see [LICENSE](LICENSE)).
The following dependencies carry their own licenses, which you must comply
with when using or distributing this software.

## PyMuPDF (fitz) — AGPL-3.0

This project depends on **[PyMuPDF](https://github.com/pymupdf/PyMuPDF)**,
which is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

> **Important:** The AGPL-3.0 license imposes obligations that differ from the
> MIT License. In particular, if you run a modified version of this software as
> a network service, the AGPL may require you to make the corresponding source
> code available to users of that service.
>
> If AGPL obligations are incompatible with your intended use, you should
> either (a) obtain a commercial license for PyMuPDF from Artifex, or
> (b) replace PyMuPDF with an alternative PDF library (e.g., `pypdfium2`,
> `pdfplumber`, or `pypdf`) under a more permissive license.

Please review the full PyMuPDF license terms before deploying this software
in production or distributing it.

## Other Notable Dependencies

| Library        | License      |
|----------------|--------------|
| FastAPI        | MIT          |
| OpenCV         | Apache-2.0   |
| Tesseract OCR  | Apache-2.0   |
| Twilio SDK     | MIT          |
| Google Cloud   | Apache-2.0   |

Refer to each library's own repository and `requirements.txt` for authoritative
license information.
