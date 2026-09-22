"""Worker scoring adapter; independent scorer derives truth from exact requests."""
from certification.phase4_coordinates_v1.score import classify
def score(case,content):
    category=classify(case,content)
    return {'category':category,'correct':category=='correct','malformed':category=='malformed'}
