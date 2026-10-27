import os
print('\n=== Sprawdzanie katalogu tests ===\n')
try:
    contents = os.listdir('tests')
    for item in contents:
        print(item)
except Exception as e:
    print(f'Błąd: {str(e)}')