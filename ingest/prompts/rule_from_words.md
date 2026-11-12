A consultant who reviews material approval forms for MEP equipment types a rule of their own, a preference on top of the law, for example "pumps only from Grundfos" or "circulation pumps come with a control panel". Turn it into one rule row:
- family: the product family it applies to, one of the families listed below, or "all"; a family not in the list is written in lower case with underscores (for example balancing_valve);
- application: for pumps only, the uses it is limited to, separated by ; (booster, circulation, dhw_circulation, dhw_charging, stormwater, drainage), else "";
- kind: "brand" (only some brands), "value" (a reading compared with a limit), "document" (a document must be attached), "included" (something must come with the product), "reminder" (anything else, checked by hand);
- field: for value and included, one of the readings listed below (join two with | when either is enough); for document, one of the document types listed below; else "";
- operator: ">=", "<=" or "=" for a value, else ""; value: the limit, or the brands separated by ;, else ""; unit: the unit of the limit, else "";
- effect: "C" when the consultant says the form must be revised or rejected, "info" when it is only a recommendation, else "B";
- text: the rule in a short plain English sentence, for example "pumps only from Grundfos".
Never add a limit or a brand the consultant did not write.
