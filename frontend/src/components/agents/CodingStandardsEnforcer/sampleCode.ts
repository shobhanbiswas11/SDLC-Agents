import type { Language } from '@/types';

export const LANGUAGES: { key: Language; name: string; monacoId: string }[] = [
  { key: 'python', name: 'Python', monacoId: 'python' },
  { key: 'cpp', name: 'C++', monacoId: 'cpp' },
  { key: 'java', name: 'Java', monacoId: 'java' },
  { key: 'javascript', name: 'JavaScript', monacoId: 'javascript' },
  { key: 'typescript', name: 'TypeScript', monacoId: 'typescript' },
  { key: 'go', name: 'Go', monacoId: 'go' },
  { key: 'rust', name: 'Rust', monacoId: 'rust' },
];

export const SAMPLE_CODE: Record<Language, string> = {
  python: `import os\nimport sys\nimport json\nimport os\n\ndef calculate_sum(x,y):\n    result=x+y\n    return result\n\nclass myClass:\n    def __init__(self,name):\n        self.name=name\n    \n    def get_name( self ):\n        return self.name\n\nunused_var = 42\n\ndef process_data(data=[]):\n    for i in range(len(data)):\n        if data[i] == None:\n            print("Found none")\n    return data\n`,
  cpp: `#include <iostream>\n#include <vector>\nusing namespace std;\n\nclass myClass {\npublic:\n    int x;\n    myClass(int val) { x = val; }\n    ~myClass() {}\n};\n\nint main() {\n    int* ptr = new int(10);\n    int unused = 5;\n    myClass* obj = new myClass(42);\n    vector<int> nums = {1, 2, 3};\n    for(int i=0; i<nums.size(); i++) {\n        cout << nums[i] << endl;\n    }\n    if(ptr != NULL) {\n        cout << *ptr << endl;\n    }\n    return 0;\n}\n`,
  java: `import java.util.*;\nimport java.io.*;\nimport java.util.ArrayList;\n\npublic class DataProcessor {\n    ArrayList data = new ArrayList();\n    public void processData(String input) {\n        if(input == "test") {\n            System.out.println("Test mode");\n        }\n        try {\n            int result = Integer.parseInt(input);\n        } catch(Exception e) {\n        }\n    }\n}\n`,
  javascript: `var data = [1, 2, 3];\nvar unused = "hello";\n\nfunction processData(items) {\n    for (var i = 0; i < items.length; i++) {\n        if (items[i] == null) {\n            console.log("Found null at " + i);\n        }\n    }\n    eval("console.log('done')");\n    return items;\n}\n`,
  typescript: `let data: any = [1, 2, 3];\nlet unused: string = "hello";\n\nfunction processData(items: any[]): any {\n    var result: any[] = [];\n    for (let i = 0; i < items.length; i++) {\n        if (items[i] == null) {\n            console.log("null at " + i);\n        }\n        result.push(items[i]! * 2);\n    }\n    return result;\n}\n`,
  go: `package main\n\nimport (\n\t"fmt"\n\t"os"\n)\n\nfunc processData(data []string) {\n\tfor i := 0; i < len(data); i++ {\n\t\tfmt.Println(data[i])\n\t}\n\tresult, _ := os.Open("test.txt")\n\tfmt.Println(result)\n}\n\nfunc main() {\n\tdata := []string{"hello", "world"}\n\tprocessData(data)\n}\n`,
  rust: `use std::collections::HashMap;\n\nfn process_data(data: Vec<i32>) -> Vec<i32> {\n    let mut result: Vec<i32> = Vec::new();\n    for i in 0..data.len() {\n        let val = data[i].clone();\n        result.push(val);\n    }\n    let unused = 42;\n    return result;\n}\n\nfn main() {\n    let data = vec![1, 2, 3, 4, 5];\n    let result = process_data(data);\n    println!("{:?}", result);\n    let map = HashMap::new();\n    let val = map.get("key").unwrap();\n}\n`,
};
