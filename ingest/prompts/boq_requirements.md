You read one line of a bill of quantities (BOQ) for MEP equipment, written in Romanian or English, and list what it asks the supplied product to have. A reviewer checks a material approval form against this list, so every item must come from the words of the line.

For each thing the line asks for, give:
- text: a few plain English words, for example "a power and control panel is included";
- kind: "included" when something must come with the product and the reading named in field says whether it does; "value" when a number is required (a pressure, a power, a voltage) and field names the reading; "brand" only when the line names brands and does not accept equivalents; "reminder" for everything else, including a reference model ("model de referinta"), "or equivalent", installation work and anything no reading covers;
- field: one of the readings listed below, or "" for a reminder; join two readings with | when either one is enough;
- operator: ">=", "<=" or "=" for a value, else "";
- value and unit: the number and its unit for a value, the brands separated by ; for a brand, else "";
- quote: the exact words of the line it comes from, at most 15 words.

A motor power is the designer's estimate: give it as a value with operator "="; the check shows it as information.

Do not list the duty (flow and head), the quantity or the unit of measure: other checks cover them. Never guess a value that is not written in the line. If the line asks for nothing else, return an empty list.
