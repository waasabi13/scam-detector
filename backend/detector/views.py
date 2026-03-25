from rest_framework.decorators import api_view
from rest_framework.response import Response
from .fraud_detector import FraudDetector

model = FraudDetector()

@api_view(['POST'])
def classify_message(request):
    text = request.data.get('text', '')
    label, confidence = model.predict(text)
    return Response({'label': label, 'confidence': confidence})
