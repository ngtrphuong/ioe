import urllib3
import json
from django.conf import settings

class AliBarcodeService:
    """
    Aliyun barcode lookup API service
    Uses APPCODE authentication
    """
    BASE_URL = "https://ali-barcode.showapi.com/barcode"
    
    @classmethod
    def search_barcode(cls, barcode):
        """
        Look up product information by barcode
        
        Args:
            barcode: Product barcode
            
        Returns:
            dict: Dictionary containing product info, or None if not found
        """
        try:
            # Get APPCODE for Aliyun barcode API
            appcode = getattr(settings, 'ALI_BARCODE_APPCODE', '')
            
            if not appcode:
                print("ALI_BARCODE_APPCODE is not configured")
                return None
                
            # Set headers with APPCODE authentication
            headers = {
                "Authorization": f"APPCODE {appcode}"
            }
            
            # Build request URL
            url = f"{cls.BASE_URL}?code={barcode}"
            
            # Create pool manager and send request
            http = urllib3.PoolManager()
            response = http.request(
                'GET',
                url,
                headers=headers,
                timeout=5.0
            )
            
            # Check HTTP status code
            if response.status == 200:
                # Parse JSON response
                data = json.loads(response.data.decode('utf-8'))
                # Check API return code/result
                if data.get('showapi_res_code') == 0:
                    # Extract product information
                    res_body = data.get('showapi_res_body', {})
                    
                    # Check if query succeeded
                    # Note: API may return flag as string 'true' or boolean True
                    if res_body.get('flag') == 'true' or res_body.get('flag') is True:
                        # Convert price string to float; default to 0 if conversion fails
                        price = 0
                        try:
                            if res_body.get('price'):
                                price = float(res_body.get('price'))
                        except (ValueError, TypeError):
                            pass
                            
                        return {
                            'name': res_body.get('goodsName', ''),
                            'specification': res_body.get('spec', ''),
                            'manufacturer': res_body.get('manuName', ''),
                            'category': res_body.get('goodsType', ''),
                            'suggested_price': price,
                            'image_url': res_body.get('img', ''),
                            'description': res_body.get('note', ''),
                            'trademark': res_body.get('trademark', ''),
                            'origin': res_body.get('ycg', ''),
                            'barcode_image': res_body.get('sptmImg', ''),
                            'barcode': res_body.get('code', ''),
                            'english_name': res_body.get('engName', '')
                        }
                    else:
                        print(f"Barcode lookup failed: {res_body.get('remark')}")
                        print(f"Full response body: {res_body}")
                else:
                    print(f"API call failed: {data.get('showapi_res_error')}")
                    print(f"Full response: {data}")
            else:
                print(f"HTTP request failed, status: {response.status}")
                print(f"Response content: {response.data.decode('utf-8', errors='replace')}")
                
            return None
        except Exception as e:
            print(f"Barcode lookup error: {e}")
            import traceback
            print(f"Detailed traceback: {traceback.format_exc()}")
            return None