import os
from difflib import unified_diff

def compare_files(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        content1 = f1.readlines()
        content2 = f2.readlines()
        
    diff = unified_diff(content1, content2, fromfile=file1, tofile=file2)
    return list(diff)

def compare_file_sets(dir1, dir2):
    files1 = set(os.listdir(dir1))
    files2 = set(os.listdir(dir2))
    
    common_files = files1.intersection(files2)
    
    report = {}
    
    for file in common_files:
        file1 = os.path.join(dir1, file)
        file2 = os.path.join(dir2, file)
        differences = compare_files(file1, file2)
        
        if differences:
            report[file] = differences
            
    return report

def print_report(report):
    for file, differences in report.items():
        print(f"Differences in file: {file}")
        for line in differences:
            print(line, end='')
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    dir1 = 'C:\\dwgmagic2\\testing\\240607_tonevi - benchmark\\scripts'
    dir2 = 'C:\\dwgmagic2\\testing\\240607_tonevi\\scripts'
    
    report = compare_file_sets(dir1, dir2)
    print_report(report)
