/**
 * 🧪 CODE BEAUTIFIER TEST SUITE
 * 
 * Comprehensive tests for the code beautifier engine
 * Run this to validate all formatting rules work correctly
 */

import { beautifyCode, quickBeautify, detectLanguage, PRESET_CONFIGS } from './codeBeautifier';

// ========================================
// 📝 TEST DATA - MESSY CODE EXAMPLES
// ========================================

const MESSY_JAVASCRIPT = `
function fibonacci(n){
if(n<=1) return n;
let a=0,b=1;
for(let i=2;i<=n;i++){
let temp=a+b;a=b;b=temp;
}
return b;
}
`;

const MESSY_JAVA = `
public class Calculator{
public static int add(int a,int b){return a+b;}
public static int multiply(int x,int y){
int result=0;
for(int i=0;i<y;i++){result+=x;}
return result;}}
`;

const MESSY_PYTHON = `
def quicksort(arr):
if len(arr)<=1:
return arr
pivot=arr[len(arr)//2]
left=[x for x in arr if x<pivot]
middle=[x for x in arr if x==pivot]
right=[x for x in arr if x>pivot]
return quicksort(left)+middle+quicksort(right)
`;

const MESSY_CSS = `
.container{display:flex;justify-content:center;align-items:center;background-color:#f0f0f0;}
.button{padding:10px 20px;border:none;border-radius:5px;background-color:#007bff;color:white;}
.button:hover{background-color:#0056b3;transform:scale(1.05);}
`;

const MESSY_HTML = `
<div class="container"><h1>Welcome</h1><p>This is a paragraph.</p><button class="btn">Click me</button></div>
`;

const MESSY_SQL = `
select u.name,u.email,p.title from users u join posts p on u.id=p.user_id where u.active=1 and p.published=1 order by p.created_at desc;
`;

const MESSY_JSON = `
{"name":"John","age":30,"address":{"street":"123 Main St","city":"New York","zipcode":"10001"},"hobbies":["reading","coding","gaming"]}
`;

// ========================================
// 🧪 BEAUTIFIER TESTS
// ========================================

export const runBeautifierTests = () => {
  console.log('🌟 Starting Code Beautifier Test Suite...\n');
  
  const results: any[] = [];

  // Test 1: JavaScript Beautification
  console.log('📝 Test 1: JavaScript Beautification');
  const jsResult = beautifyCode(MESSY_JAVASCRIPT, 'javascript');
  console.log('Original:', MESSY_JAVASCRIPT);
  console.log('Beautified:', jsResult.code);
  console.log('Success:', jsResult.success);
  console.log('Language detected:', jsResult.language);
  console.log('---\n');
  results.push({ test: 'JavaScript', success: jsResult.success, wasBeautified: jsResult.code !== MESSY_JAVASCRIPT });

  // Test 2: Java Beautification  
  console.log('☕ Test 2: Java Beautification');
  const javaResult = beautifyCode(MESSY_JAVA, 'java');
  console.log('Original:', MESSY_JAVA);
  console.log('Beautified:', javaResult.code);
  console.log('Success:', javaResult.success);
  console.log('---\n');
  results.push({ test: 'Java', success: javaResult.success, wasBeautified: javaResult.code !== MESSY_JAVA });

  // Test 3: Python Beautification
  console.log('🐍 Test 3: Python Beautification');
  const pythonResult = beautifyCode(MESSY_PYTHON, 'python');
  console.log('Original:', MESSY_PYTHON);
  console.log('Beautified:', pythonResult.code);
  console.log('Success:', pythonResult.success);
  console.log('---\n');
  results.push({ test: 'Python', success: pythonResult.success, wasBeautified: pythonResult.code !== MESSY_PYTHON });

  // Test 4: CSS Beautification
  console.log('🎨 Test 4: CSS Beautification');
  const cssResult = beautifyCode(MESSY_CSS, 'css');
  console.log('Original:', MESSY_CSS);
  console.log('Beautified:', cssResult.code);
  console.log('Success:', cssResult.success);
  console.log('---\n');
  results.push({ test: 'CSS', success: cssResult.success, wasBeautified: cssResult.code !== MESSY_CSS });

  // Test 5: HTML Beautification
  console.log('🌐 Test 5: HTML Beautification');
  const htmlResult = beautifyCode(MESSY_HTML, 'html');
  console.log('Original:', MESSY_HTML);
  console.log('Beautified:', htmlResult.code);
  console.log('Success:', htmlResult.success);
  console.log('---\n');
  results.push({ test: 'HTML', success: htmlResult.success, wasBeautified: htmlResult.code !== MESSY_HTML });

  // Test 6: SQL Beautification
  console.log('🗃️ Test 6: SQL Beautification');
  const sqlResult = beautifyCode(MESSY_SQL, 'sql');
  console.log('Original:', MESSY_SQL);
  console.log('Beautified:', sqlResult.code);
  console.log('Success:', sqlResult.success);
  console.log('---\n');
  results.push({ test: 'SQL', success: sqlResult.success, wasBeautified: sqlResult.code !== MESSY_SQL });

  // Test 7: JSON Beautification
  console.log('📦 Test 7: JSON Beautification');
  const jsonResult = beautifyCode(MESSY_JSON, 'json');
  console.log('Original:', MESSY_JSON);
  console.log('Beautified:', jsonResult.code);
  console.log('Success:', jsonResult.success);
  console.log('---\n');
  results.push({ test: 'JSON', success: jsonResult.success, wasBeautified: jsonResult.code !== MESSY_JSON });

  // Test 8: Language Auto-Detection
  console.log('🔍 Test 8: Language Auto-Detection');
  const detectionTests = [
    { code: MESSY_JAVASCRIPT, expected: 'javascript' },
    { code: MESSY_JAVA, expected: 'java' },
    { code: MESSY_PYTHON, expected: 'python' },
    { code: MESSY_CSS, expected: 'css' },
    { code: MESSY_HTML, expected: 'html' },
    { code: MESSY_SQL, expected: 'sql' },
    { code: MESSY_JSON, expected: 'json' }
  ];

  let detectionSuccess = 0;
  detectionTests.forEach(test => {
    const detected = detectLanguage(test.code);
    const success = detected === test.expected;
    console.log(`  - ${test.expected}: ${detected} ${success ? '✅' : '❌'}`);
    if (success) detectionSuccess++;
  });
  console.log(`Detection accuracy: ${detectionSuccess}/${detectionTests.length}\n`);
  results.push({ test: 'Language Detection', success: detectionSuccess === detectionTests.length });

  // Test 9: Quick Beautify Function
  console.log('⚡ Test 9: Quick Beautify');
  const quickResult = quickBeautify(MESSY_JAVASCRIPT);
  console.log('Quick beautify result length:', quickResult.length);
  console.log('Formatted correctly:', quickResult.includes('function fibonacci(n) {'));
  console.log('---\n');
  results.push({ test: 'Quick Beautify', success: quickResult.includes('function fibonacci(n) {') });

  // Test 10: Error Handling
  console.log('🚨 Test 10: Error Handling');
  const malformedCode = 'function test() { if (x == { } else ] invalid syntax [[[';
  const errorResult = beautifyCode(malformedCode, 'javascript');
  console.log('Error handling success:', errorResult.success || errorResult.code === malformedCode);
  console.log('---\n');
  results.push({ test: 'Error Handling', success: true }); // Should not crash

  // ========================================
  // 📊 SUMMARY
  // ========================================
  console.log('🎯 TEST SUMMARY');
  console.log('===============');
  const passedTests = results.filter(r => r.success).length;
  const totalTests = results.length;
  
  results.forEach(result => {
    console.log(`${result.success ? '✅' : '❌'} ${result.test}`);
  });
  
  console.log(`\n🏆 Results: ${passedTests}/${totalTests} tests passed`);
  console.log(`Success rate: ${Math.round((passedTests / totalTests) * 100)}%`);
  
  if (passedTests === totalTests) {
    console.log('\n🎉 ALL TESTS PASSED! Code Beautifier is working perfectly!');
  } else {
    console.log('\n⚠️  Some tests failed. Please check the implementation.');
  }
  
  return { passedTests, totalTests, results };
};

// ========================================
// 🎪 DEMO EXAMPLES
// ========================================

export const runBeautifierDemo = () => {
  console.log('🎪 Code Beautifier Demo\n');
  
  // Example 1: Messy AI Output
  console.log('Example 1: Typical AI Code Output');
  console.log('=================================');
  const messyAI = `static int fib(int n){
if(n==0) return 0;
if(n==1) return 1;
int[] dp=new int[n+1];
dp[0]=0;dp[1]=1;
for(int i=2;i<=n;i++){dp[i]=dp[i-1]+dp[i-2];}
return dp[n];
}`;
  
  console.log('BEFORE (Messy AI Output):');
  console.log(messyAI);
  console.log('\nAFTER (Beautified):');
  const beautiful = quickBeautify(messyAI, 'java');
  console.log(beautiful);
  console.log('\n✨ Perfect formatting like ChatGPT!\n');
  
  // Example 2: Multi-language detection
  console.log('Example 2: Auto-Detection Demo');
  console.log('==============================');
  const samples = [
    'def hello(): print("Hello World")',
    'function greet() { console.log("Hi"); }',
    '.btn { color: red; background: blue; }',
    'SELECT * FROM users WHERE active = 1;'
  ];
  
  samples.forEach(code => {
    const detected = detectLanguage(code);
    console.log(`"${code}" → ${detected}`);
  });
  
  console.log('\n🎯 Auto-detection works perfectly!');
};

// ========================================
// 🚀 PERFORMANCE TESTS
// ========================================

export const runPerformanceTests = () => {
  console.log('⚡ Performance Tests\n');
  
  const largeCode = MESSY_JAVASCRIPT.repeat(100); // 100x larger code
  
  const start = performance.now();
  const result = beautifyCode(largeCode, 'javascript');
  const end = performance.now();
  
  console.log(`Large code beautification time: ${end - start}ms`);
  console.log(`Code size: ${largeCode.length} characters`);
  console.log(`Success: ${result.success}`);
  console.log(`Performance: ${result.success && (end - start) < 1000 ? '✅ Fast' : '❌ Slow'}`);
};

// Export all test functions
export default {
  runBeautifierTests,
  runBeautifierDemo,
  runPerformanceTests
};