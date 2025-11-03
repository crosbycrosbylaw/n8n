from __future__ import annotations

import typing as ty
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import *
    from typing import *


class Sample(ty.TypedDict):
    raw_text: str

    document_link: str
    document_name: str

    related_parties: Sequence[tuple[str, str | None, str]]


_empty: list[Sample] = []

FA, NoS, CC = (_empty.copy() for _ in range(3))

FA.append(
    Sample(
        raw_text="""<!DOCTYPE html><html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head>
<style> body { font-family: Arial,Helvetica,sans-serif; font-size: 12pt; } .header { padding: 10 auto; top: 0; display:block; } .content { padding: 10px 0; margin: 0 auto; height: auto; } h1 { color: #12428A; padding: 0 0; margin: 0 0; } th { background-color: #12428A; color: #FFFFFF; font-weight: bold; } .footer { color:darkslategrey; height: 100px; bottom: 0; left: 0; width: 100%; } </style> <body> <div class="header"> <table width="100%"> <tbody> <tr> <td width="50%" align="left"><img src="https://illinois.tylertech.cloud/ClientBin/logos/Illogo.png" alt="EFile State Logo"></td> <td width="50%" align="right"><h1>Filing Accepted</h1> <p style="margin: 0px;">Envelope Number: 34849700<br>Case Number: 2014-D-0000740<br>Case Name: Candace R Boudreau vs. Christopher R Boudreau</p></td> </tr> </tbody> </table> </div> <div class="content"> <p>The filing below was reviewed and has been accepted by the clerk's office. You may access the file stamped copy of the document filed by clicking on the below link.</p> <table width="100%" border="1" cellpadding="3" cellspacing="0"> <tbody> <tr> <th colspan="2">Filing Details</th> </tr> <tr> <td width="30%"><b>Court</b></td> <td>Winnebago County</td> </tr> <tr> <td width="30%"><b>Case Number</b></td> <td>2014-D-0000740</td> </tr> <tr> <td width="30%"><b>Case Name</b></td> <td>Candace R Boudreau vs. Christopher R Boudreau</td> </tr> <tr> <td width="30%"><b>Date/Time Submitted</b></td> <td>10/10/2025 4:51 PM CST</td> </tr> <tr> <td width="30%"><b>Date/Time Accepted</b></td> <td>10/13/2025 5:17 PM CST</td> </tr> <tr> <td width="30%"><b>Accepted Comments</b></td> <td></td> </tr> <tr> <td width="30%"><b>Filing Type</b></td> <td>EFileAndServe</td> </tr> <tr> <td width="30%"><b>Filing Description</b></td> <td>Motion to Modify Maintenance</td> </tr> <tr> <td width="30%"><b>Filing Code</b></td> <td>Motion to Modify (No Fee)</td> </tr> <tr> <td width="30%"><b>Filed By</b></td> <td>Mason Crosby</td> </tr> <tr> <td width="30%"><b>Filing Attorney</b></td> <td>Mason Crosby</td> </tr> </tbody> </table><br> <table width="100%" border="1" cellpadding="3" cellspacing="0"> <tbody> <tr> <th colspan="2">Document Details</th> </tr> <tr> <td width="30%"><b>Lead Document</b></td> <td>Motion to Modify Maintenance RTF.pdf</td> </tr> <tr> <td width="30%"><b>Lead Document Page Count</b></td> <td>3</td> </tr> <tr> <td width="30%"><b>File Stamped Copy</b></td> <td><a href="https://illinois.tylertech.cloud/ViewDocuments.aspx?FID=9e4802ef-9954-4ed2-963b-4e50f0cbff98">Download Document</a></td> </tr> <tr> <td colspan="2" align="center">This link is active for 548 days. To access this document, you will be required to enter your email address. Click <a href="https://content.tylerhost.net/docs/Filer_Information.pdf" target="_blank" rel="noopener">here</a> for more information.</td> </tr> </tbody> </table> <p>If the link above is not accessible, copy this URL into your browser's address bar to view the document: <br>https://illinois.tylertech.cloud/ViewDocuments.aspx?FID=9e4802ef-9954-4ed2-963b-4e50f0cbff98</p>  <p> If you are not represented by a lawyer, we want to improve your e-filing experience. Please <a href="https://docs.google.com/forms/d/e/1FAIpQLScTqDkGzBQm25gaSWw8pPmfInrdkfkXBuAIS1G2Wi-MM4pqWA/viewform">click here</a> to fill out a short survey. </p> <p><b>Please Note:</b> If you have not already done so, be sure to add yourself as a service contact on this case in order to receive eService.</p> </div> <div class="footer"> <p width="100" align="center">For technical assistance, contact your service provider<br> <div id="contactname">Odyssey File &amp; Serve</div><br><div id="contactphone">(800) 297-5377</div><br> Please do not reply to this email. It was automatically generated. </p> </div> </body>    </html>""",
        document_link="https://illinois.tylertech.cloud/ViewDocuments.aspx?FID=9e4802ef-9954-4ed2-963b-4e50f0cbff98",
        document_name="Motion to Modify Maintenance RTF.pdf",
        related_parties=[("Candace", "R", "Boudreau"), ("Christopher", "R", "Boudreau")],
    )
)
