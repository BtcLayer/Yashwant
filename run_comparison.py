# Run comparison and save output
import subprocess
result = subprocess.run(['python', 'compare_models.py'], capture_output=True, text=True, cwd=r'c:\Users\yashw\MetaStackerBandit')
with open(r'c:\Users\yashw\MetaStackerBandit\comparison_result.txt', 'w', encoding='utf-8') as f:
    f.write(result.stdout)
    if result.stderr:
        f.write('\n\n=== STDERR ===\n')
        f.write(result.stderr)
print("Output saved to comparison_result.txt")
