/**
 * 🧪 CODE BEAUTIFIER TEST PAGE
 * 
 * Interactive demo page to test the code beautifier
 * Access via: /beautifier-test (for development)
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CodeBlock } from '@/components/chat/CodeBlock';
import { beautifyCode, detectLanguage, PRESET_CONFIGS } from '@/lib/codeBeautifier';
import { runBeautifierTests, runBeautifierDemo } from '@/lib/beautifierTests';
import { 
  Sparkles, 
  Play, 
  RotateCcw, 
  Code2, 
  TestTube, 
  Zap,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';

const SAMPLE_CODES = {
  messyJavaScript: `function fibonacci(n){
if(n<=1) return n;
let a=0,b=1;
for(let i=2;i<=n;i++){
let temp=a+b;a=b;b=temp;
}
return b;
}`,
  messyJava: `public class Calculator{
public static int add(int a,int b){return a+b;}
public static int multiply(int x,int y){
int result=0;
for(int i=0;i<y;i++){result+=x;}
return result;}}`,
  messyPython: `def quicksort(arr):
if len(arr)<=1:
return arr
pivot=arr[len(arr)//2]
left=[x for x in arr if x<pivot]
middle=[x for x in arr if x==pivot]
right=[x for x in arr if x>pivot]
return quicksort(left)+middle+quicksort(right)`,
  messyCSS: `.container{display:flex;justify-content:center;align-items:center;background-color:#f0f0f0;}
.button{padding:10px 20px;border:none;border-radius:5px;background-color:#007bff;color:white;}
.button:hover{background-color:#0056b3;transform:scale(1.05);}`,
  messyHTML: `<div class="container"><h1>Welcome</h1><p>This is a paragraph.</p><button class="btn">Click me</button></div>`,
  messySQL: `select u.name,u.email,p.title from users u join posts p on u.id=p.user_id where u.active=1 and p.published=1 order by p.created_at desc;`,
  messyJSON: `{"name":"John","age":30,"address":{"street":"123 Main St","city":"New York","zipcode":"10001"},"hobbies":["reading","coding","gaming"]}`
};

export const BeautifierTestPage = () => {
  const [inputCode, setInputCode] = useState(SAMPLE_CODES.messyJavaScript);
  const [selectedLanguage, setSelectedLanguage] = useState('auto');
  const [result, setResult] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [testResults, setTestResults] = useState<any>(null);
  const [selectedSample, setSelectedSample] = useState('messyJavaScript');

  const handleBeautify = async () => {
    setIsProcessing(true);
    
    // Simulate some processing time for effect
    await new Promise(resolve => setTimeout(resolve, 300));
    
    const language = selectedLanguage === 'auto' ? undefined : selectedLanguage;
    const beautified = beautifyCode(inputCode, language);
    
    setResult(beautified);
    setIsProcessing(false);
  };

  const handleRunTests = () => {
    console.log('🧪 Running comprehensive beautifier tests...');
    const results = runBeautifierTests();
    setTestResults(results);
    
    // Also run the demo
    runBeautifierDemo();
  };

  const handleLoadSample = (sampleKey: string) => {
    setInputCode(SAMPLE_CODES[sampleKey as keyof typeof SAMPLE_CODES]);
    setSelectedSample(sampleKey);
    setResult(null);
  };

  const detectedLanguage = detectLanguage(inputCode);

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-6xl">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-2">
          <Sparkles className="w-8 h-8 text-yellow-500" />
          <h1 className="text-3xl font-bold">Code Beautifier Test Lab</h1>
        </div>
        <p className="text-muted-foreground">
          Interactive testing environment for the AI code beautification engine
        </p>
      </div>

      <Tabs defaultValue="interactive" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="interactive" className="gap-2">
            <Code2 className="w-4 h-4" />
            Interactive Test
          </TabsTrigger>
          <TabsTrigger value="automated" className="gap-2">
            <TestTube className="w-4 h-4" />
            Automated Tests
          </TabsTrigger>
          <TabsTrigger value="examples" className="gap-2">
            <Zap className="w-4 h-4" />
            Live Examples
          </TabsTrigger>
        </TabsList>

        {/* Interactive Testing */}
        <TabsContent value="interactive" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Input Panel */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code2 className="w-5 h-5" />
                  Input Code
                </CardTitle>
                <CardDescription>
                  Paste messy code to beautify, or select a sample
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Sample Selector */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Load Sample:</label>
                  <Select value={selectedSample} onValueChange={handleLoadSample}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="messyJavaScript">JavaScript (Function)</SelectItem>
                      <SelectItem value="messyJava">Java (Class)</SelectItem>
                      <SelectItem value="messyPython">Python (Algorithm)</SelectItem>
                      <SelectItem value="messyCSS">CSS (Styles)</SelectItem>
                      <SelectItem value="messyHTML">HTML (Structure)</SelectItem>
                      <SelectItem value="messySQL">SQL (Query)</SelectItem>
                      <SelectItem value="messyJSON">JSON (Data)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Language Override */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Language: 
                    <Badge variant="outline" className="ml-2">
                      Detected: {detectedLanguage}
                    </Badge>
                  </label>
                  <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">Auto-detect</SelectItem>
                      <SelectItem value="javascript">JavaScript</SelectItem>
                      <SelectItem value="java">Java</SelectItem>
                      <SelectItem value="python">Python</SelectItem>
                      <SelectItem value="css">CSS</SelectItem>
                      <SelectItem value="html">HTML</SelectItem>
                      <SelectItem value="sql">SQL</SelectItem>
                      <SelectItem value="json">JSON</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Code Input */}
                <Textarea
                  value={inputCode}
                  onChange={(e) => setInputCode(e.target.value)}
                  placeholder="Paste your messy code here..."
                  className="min-h-48 font-mono text-sm"
                />

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <Button 
                    onClick={handleBeautify} 
                    disabled={isProcessing || !inputCode.trim()}
                    className="flex-1"
                  >
                    {isProcessing ? (
                      <>
                        <Clock className="w-4 h-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4 mr-2" />
                        Beautify Code
                      </>
                    )}
                  </Button>
                  
                  <Button 
                    variant="outline" 
                    onClick={() => { setInputCode(''); setResult(null); }}
                  >
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Output Panel */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-yellow-500" />
                  Beautified Result
                  {result?.success && (
                    <Badge variant="default" className="gap-1">
                      <CheckCircle className="w-3 h-3" />
                      Success
                    </Badge>
                  )}
                  {result?.success === false && (
                    <Badge variant="destructive" className="gap-1">
                      <XCircle className="w-3 h-3" />
                      Failed
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription>
                  Automatically formatted and beautified code
                </CardDescription>
              </CardHeader>
              <CardContent>
                {result ? (
                  <div className="space-y-4">
                    {/* Stats */}
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>Language: <Badge variant="secondary">{result.language}</Badge></div>
                      <div>Success: {result.success ? '✅' : '❌'}</div>
                    </div>

                    {/* Code Display */}
                    {result.success ? (
                      <CodeBlock language={result.language}>
                        {result.code}
                      </CodeBlock>
                    ) : (
                      <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                        <p className="text-destructive text-sm">
                          Beautification failed: {result.errors?.join(', ')}
                        </p>
                        <pre className="mt-2 text-xs opacity-70">
                          {inputCode}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground">
                    Click "Beautify Code" to see the result
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Automated Tests */}
        <TabsContent value="automated" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TestTube className="w-5 h-5" />
                Comprehensive Test Suite
              </CardTitle>
              <CardDescription>
                Run automated tests to validate beautifier functionality
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Button onClick={handleRunTests} className="w-full" size="lg">
                  <Play className="w-4 h-4 mr-2" />
                  Run All Tests
                </Button>

                {testResults && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-4"
                  >
                    {/* Overall Results */}
                    <div className="p-4 bg-secondary/50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium">Test Results</h4>
                        <Badge variant={testResults.passedTests === testResults.totalTests ? "default" : "destructive"}>
                          {testResults.passedTests}/{testResults.totalTests} Passed
                        </Badge>
                      </div>
                      <Progress 
                        value={(testResults.passedTests / testResults.totalTests) * 100} 
                        className="mb-2"
                      />
                      <p className="text-sm text-muted-foreground">
                        Success Rate: {Math.round((testResults.passedTests / testResults.totalTests) * 100)}%
                      </p>
                    </div>

                    {/* Individual Test Results */}
                    <div className="space-y-2">
                      {testResults.results.map((result: any, index: number) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-muted/30 rounded">
                          <span className="text-sm">{result.test}</span>
                          {result.success ? (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          ) : (
                            <XCircle className="w-4 h-4 text-red-500" />
                          )}
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Live Examples */}
        <TabsContent value="examples" className="space-y-6">
          <div className="grid gap-6">
            {Object.entries(SAMPLE_CODES).map(([key, code]) => {
              const language = detectLanguage(code);
              const beautified = beautifyCode(code, language);
              
              return (
                <Card key={key}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <Code2 className="w-5 h-5" />
                      {language.charAt(0).toUpperCase() + language.slice(1)} Example
                      <Badge variant="outline">{language}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-2 gap-4">
                      {/* Before */}
                      <div>
                        <h4 className="text-sm font-medium mb-2 text-muted-foreground">BEFORE (Messy)</h4>
                        <pre className="text-xs bg-muted/50 p-3 rounded border overflow-auto max-h-48">
                          {code}
                        </pre>
                      </div>
                      
                      {/* After */}
                      <div>
                        <h4 className="text-sm font-medium mb-2 text-muted-foreground flex items-center gap-1">
                          AFTER 
                          <Sparkles className="w-3 h-3 text-yellow-500" />
                          (Beautified)
                        </h4>
                        <div className="max-h-48 overflow-auto">
                          <CodeBlock language={language}>
                            {beautified.code}
                          </CodeBlock>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>
      </Tabs>

      {/* Console Output Notice */}
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">
            💡 <strong>Tip:</strong> Open browser console (F12) to see detailed beautifier logs and test output
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default BeautifierTestPage;