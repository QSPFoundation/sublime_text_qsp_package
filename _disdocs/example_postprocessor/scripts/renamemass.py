import sys, os
import re

# скрипт заменяет числовой массив mass на fruit_count, а текстовый на $fruit_name
def main(qsps):
    with open(qsps,'r',encoding="utf-16-le") as file:
        string_list=file.readlines()
    new_string_list=[]
    for string in string_list:
        run = True
        while run:
            mass_string=re.search(r'\$mass\b',string)
            if mass_string!=None:
                string=string.replace(mass_string.group(0),'$fruit_name',1)
            else:
                run=False
                break
        run = True
        while run:
            mass_string=re.search(r'\bmass\b',string)
            if mass_string!=None:
                string=string.replace(mass_string.group(0),'fruit_count',1)
            else:
                run=False
                break
        new_string_list.append(string)
    with open(qsps,'w',encoding="utf-16-le") as file:
        file.writelines(new_string_list)

if __name__=="__main__":
    main(os.path.abspath(sys.argv[1]))

