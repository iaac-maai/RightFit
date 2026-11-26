# -*- coding: utf-8 -*-
"""Runs once when pyRevit loads RightFit: starts listening for "Preview in Revit" messages from RightFit online
(spec/features/revit_link.md §9). It does nothing until this computer and a project folder are linked (RightFit ›
Online), and never stops pyRevit from loading."""
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
if LIB not in sys.path:
    sys.path.append(LIB)

try:
    import rf_listen
    rf_listen.start()
except Exception:
    pass
