from flask import Blueprint, request, jsonify
import requests
import os
from flask_cors import CORS

openai_proxy_bp = Blueprint('openai_proxy', __name__)

# تمكين CORS لهذا Blueprint
CORS(openai_proxy_bp)

@openai_proxy_bp.route('/generate-content', methods=['POST', 'OPTIONS'])
def generate_content():
    """
    خادم وكيل آمن لـ OpenAI API
    يستقبل طلبات من الواجهة الأمامية ويرسلها إلى OpenAI API
    """
    
    # التعامل مع طلبات OPTIONS للـ CORS
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    try:
        # الحصول على البيانات من الطلب
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'لا توجد بيانات في الطلب'}), 400
        
        campaign_topic = data.get('campaignTopic', '')
        api_key = data.get('apiKey', '')
        
        if not campaign_topic:
            return jsonify({'error': 'موضوع الحملة مطلوب'}), 400
        
        if not api_key:
            return jsonify({'error': 'مفتاح OpenAI API مطلوب'}), 400
        
        # إعداد الطلب إلى OpenAI API
        openai_url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # إنشاء prompt محسن لتوليد محتوى البريد الإلكتروني
        prompt = f"""
أنت خبير في كتابة رسائل البريد الإلكتروني التسويقية. أريدك أن تنشئ محتوى بريد إلكتروني احترافي ومقنع حول الموضوع التالي: "{campaign_topic}"

يجب أن يتضمن المحتوى الأقسام التالية بالضبط:

1. عنوان جذاب (لا يزيد عن 60 حرف)
2. مقدمة مشوقة (2-3 جمل)
3. وصف العرض أو المنتج (فقرة واحدة مفصلة)
4. نص زر الدعوة لاتخاذ إجراء (لا يزيد عن 25 حرف)

يرجى تنسيق الإجابة كـ JSON بالشكل التالي:
{{
  "title": "العنوان هنا",
  "introduction": "المقدمة هنا",
  "description": "وصف العرض هنا",
  "cta": "نص زر CTA هنا"
}}

تأكد من أن المحتوى باللغة العربية ومناسب للجمهور العربي.
"""
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "أنت مساعد ذكي متخصص في كتابة محتوى البريد الإلكتروني التسويقي باللغة العربية."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        # إرسال الطلب إلى OpenAI API
        response = requests.post(openai_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            openai_response = response.json()
            
            # استخراج المحتوى المولّد
            if 'choices' in openai_response and len(openai_response['choices']) > 0:
                generated_content = openai_response['choices'][0]['message']['content']
                
                try:
                    # محاولة تحليل JSON من الاستجابة
                    import json
                    content_json = json.loads(generated_content)
                    
                    # التحقق من وجود جميع الحقول المطلوبة
                    required_fields = ['title', 'introduction', 'description', 'cta']
                    if all(field in content_json for field in required_fields):
                        return jsonify({
                            'success': True,
                            'content': content_json
                        })
                    else:
                        # إذا لم تكن الاستجابة بصيغة JSON صحيحة، نحاول تحليلها يدوياً
                        return jsonify({
                            'success': True,
                            'content': {
                                'title': f"عرض رائع: {campaign_topic}",
                                'introduction': f"اكتشف أفضل العروض المتاحة حول {campaign_topic}",
                                'description': generated_content[:200] + "...",
                                'cta': "اكتشف الآن"
                            }
                        })
                        
                except json.JSONDecodeError:
                    # في حالة فشل تحليل JSON، نرجع محتوى افتراضي
                    return jsonify({
                        'success': True,
                        'content': {
                            'title': f"عرض رائع: {campaign_topic}",
                            'introduction': f"اكتشف أفضل العروض المتاحة حول {campaign_topic}",
                            'description': generated_content[:200] + "...",
                            'cta': "اكتشف الآن"
                        }
                    })
            else:
                return jsonify({'error': 'لم يتم إنشاء محتوى من OpenAI'}), 500
                
        else:
            error_message = f"خطأ من OpenAI API: {response.status_code}"
            if response.text:
                error_message += f" - {response.text}"
            return jsonify({'error': error_message}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'انتهت مهلة الاتصال مع OpenAI API'}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'خطأ في الاتصال: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'خطأ غير متوقع: {str(e)}'}), 500

@openai_proxy_bp.route('/health', methods=['GET'])
def health_check():
    """فحص صحة الخادم"""
    return jsonify({'status': 'healthy', 'message': 'خادم OpenAI Proxy يعمل بشكل طبيعي'})

