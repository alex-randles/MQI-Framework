from modules.validate_quality import ValidateQuality
import json
t = ValidateQuality(
    "/home/alex/Music/mapping.ttl")
print(json.dumps(t.validation_results, indent=4))