"""
CSV file utility functions
"""
import csv
import io


def validate_csv(csv_file, required_headers=None, expected_headers=None, max_rows=1000):
    """
    Validate the CSV file format and content.
    
    Args:
    - csv_file: Uploaded CSV file object
    - required_headers: Required column headers
    - expected_headers: Optional/expected column headers
    - max_rows: Maximum allowed rows
    
    Returns:
    - dict: Validation result
    """
    if required_headers is None:
        required_headers = []
    if expected_headers is None:
        expected_headers = []
    
    # Reset file pointer
    csv_file.seek(0)
    
    # Read CSV file
    try:
        csv_data = csv_file.read().decode('utf-8-sig')  # Handle UTF-8 with BOM
    except UnicodeDecodeError:
        try:
            # Try alternative encodings
            csv_file.seek(0)
            csv_data = csv_file.read().decode('gb18030')  # Common on Chinese Windows
        except UnicodeDecodeError:
            return {
                'valid': False,
                'errors': 'Unable to parse CSV encoding. Please save as UTF-8 or GB18030.'
            }
    
    # Create CSV reader
    csv_reader = csv.reader(io.StringIO(csv_data))
    
    # Read header row
    try:
        headers = next(csv_reader)
    except StopIteration:
        return {
            'valid': False,
            'errors': 'CSV file is empty or invalid format'
        }
    
    # Validate required headers
    missing_headers = [header for header in required_headers if header not in headers]
    if missing_headers:
        return {
            'valid': False,
            'errors': f'Missing required columns: {", ".join(missing_headers)}'
        }
    
    # Validate row count
    row_count = 1  # Already read header row
    for _ in csv_reader:
        row_count += 1
        if row_count > max_rows:
            return {
                'valid': False,
                'errors': f'CSV file row count exceeds limit ({max_rows} rows)'
            }
    
    # Reset file pointer for subsequent uses
    csv_file.seek(0)
    
    return {
        'valid': True,
        'headers': headers,
        'row_count': row_count
    }


def validate_csv_data(csv_file, validators=None, required_headers=None):
    """
    Validate CSV data rows according to provided rules.
    
    Args:
    - csv_file: Uploaded CSV file object
    - validators: Dict of field -> validator callables
    - required_headers: Required column headers
    
    Returns:
    - dict: Validation result
    """
    if validators is None:
        validators = {}
    if required_headers is None:
        required_headers = []
    
    # First validate basic CSV structure
    basic_validation = validate_csv(csv_file, required_headers=required_headers)
    if not basic_validation['valid']:
        return basic_validation
    
    # Reset file pointer
    csv_file.seek(0)
    
    # Read CSV content
    csv_data = csv_file.read().decode('utf-8-sig')
    csv_reader = csv.DictReader(io.StringIO(csv_data))
    
    errors = []
    row_num = 2  # Start from 2 (1 is header row)
    
    # Validate rows one by one
    for row in csv_reader:
        row_errors = []
        
        # Check required fields are not empty
        for header in required_headers:
            if not row.get(header):
                row_errors.append(f'Column "{header}" cannot be empty')
        
        # Apply custom validators
        for field, validator in validators.items():
            if field in row:
                try:
                    validator_result = validator(row[field])
                    if validator_result is not True:
                        row_errors.append(f'Column "{field}": {validator_result}')
                except Exception as e:
                    row_errors.append(f'Validation error for column "{field}": {str(e)}')
        
        if row_errors:
            errors.append((row_num, row_errors))
        
        row_num += 1
    
    # Reset file pointer for subsequent uses
    csv_file.seek(0)
    
    if errors:
        return {
            'valid': False,
            'errors': f'CSV data validation failed; {len(errors)} rows have issues',
            'detail_errors': errors
        }
    
    return {
        'valid': True,
        'row_count': row_num - 1  # Exclude header row
    } 