import os
import sys
from google.cloud import geminidataanalytics

classes_to_inspect = [
    "SystemMessage",
    "TextMessage",
    "DataMessage",
    "ChartMessage",
    "ErrorMessage",
    "ExampleQueries",
    "ExampleQuery",
    "ChartResult",
    "ChartQuery"
]

for name in classes_to_inspect:
    print(f"\n==========================================")
    print(f"Inspecting {name}")
    print(f"==========================================")
    cls = getattr(geminidataanalytics, name)
    try:
        instance = cls()
        print("Attributes:")
        for attr in dir(instance):
            if not attr.startswith("_"):
                print(f"- {attr}")
    except Exception as e:
        print(f"Error instantiating/inspecting {name}: {e}")
