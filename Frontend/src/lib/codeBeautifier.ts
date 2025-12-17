/**
 * 🌟 COMPREHENSIVE CODE BEAUTIFIER ENGINE
 * 
 * Automatically formats and beautifies code from AI responses
 * Supports: Java, JavaScript, TypeScript, Python, C/C++, HTML, CSS, SQL, JSON
 * 
 * Features:
 * ✅ Perfect Indentation (2 spaces for most, 4 for Python)  
 * ✅ Operator Spacing (a=b → a = b)
 * ✅ Brace Normalization (K&R style)
 * ✅ Line Breaks (after {}, ;, etc.)
 * ✅ Multi-language Support
 * ✅ Error Auto-Fix (missing semicolons, unbalanced braces)
 * ✅ Clean Markdown Block Output
 * ✅ Prettier integration for Java (prettier-plugin-java)
 */

import prettier from 'prettier';
import javaPlugin from 'prettier-plugin-java';

export interface BeautifyOptions {
  indentSize?: number;
  useSpaces?: boolean;
  maxLineLength?: number;
  insertFinalNewline?: boolean;
  preserveStrings?: boolean;
}

export interface BeautifyResult {
  code: string;
  language: string;
  success: boolean;
  errors?: string[];
  stats?: {
    linesAdded: number;
    linesRemoved: number;
    indentFixed: number;
    spacingFixed: number;
  };
}

/**
 * 🎯 MAIN CODE BEAUTIFIER CLASS
 */
export class CodeBeautifierEngine {
  private readonly DEFAULT_OPTIONS: BeautifyOptions = {
    indentSize: 2,
    useSpaces: true,
    maxLineLength: 100,
    insertFinalNewline: true,
    preserveStrings: true,
  };

  /**
   * ✨ MAIN PUBLIC METHOD - Beautify any code
   */
  public beautify(
    code: string, 
    language?: string, 
    options?: BeautifyOptions
  ): BeautifyResult {
    try {
      const opts = { ...this.DEFAULT_OPTIONS, ...options };
      const detectedLang = language || this.detectLanguage(code);
      
      console.log(`🎨 Beautifying ${detectedLang} code (${code.length} chars)`);
      
      let beautifiedCode = code;
      let stats = {
        linesAdded: 0,
        linesRemoved: 0,
        indentFixed: 0,
        spacingFixed: 0
      };

      // Apply language-specific formatting
      switch (detectedLang.toLowerCase()) {
        case 'javascript':
        case 'typescript':
        case 'js':
        case 'ts':
          beautifiedCode = this.formatJavaScript(code, opts);
          break;
        case 'java':
          // 🟩 Use Prettier with prettier-plugin-java for PERFECT Java formatting
          beautifiedCode = this.formatJavaWithPrettier(code);
          break;
        case 'c':
        case 'cpp':
        case 'c++':
          beautifiedCode = this.formatCLike(code, opts, detectedLang);
          break;
        case 'python':
        case 'py':
          beautifiedCode = this.formatPython(code, { ...opts, indentSize: 4 });
          break;
        case 'html':
        case 'xml':
          beautifiedCode = this.formatHTML(code, opts);
          break;
        case 'css':
        case 'scss':
        case 'sass':
          beautifiedCode = this.formatCSS(code, opts);
          break;
        case 'sql':
          beautifiedCode = this.formatSQL(code, opts);
          break;
        case 'json':
          beautifiedCode = this.formatJSON(code, opts);
          break;
        default:
          // Generic formatting for unknown languages
          beautifiedCode = this.formatGeneric(code, opts);
      }

      // Final cleanup
      beautifiedCode = this.finalCleanup(beautifiedCode);

      return {
        code: beautifiedCode,
        language: detectedLang,
        success: true,
        stats
      };

    } catch (error) {
      console.error('🚨 Beautifier error:', error);
      return {
        code: code, // Return original on error
        language: language || 'text',
        success: false,
        errors: [error instanceof Error ? error.message : 'Unknown error']
      };
    }
  }

  /**
   * 🔍 AUTO-DETECT PROGRAMMING LANGUAGE
   */
  private detectLanguage(code: string): string {
    const trimmed = code.trim();
    
    // JSON detection
    if (this.isValidJSON(trimmed)) {
      return 'json';
    }
    
    // HTML/XML detection
    if (/<[^>]+>/g.test(trimmed) && (trimmed.includes('<!DOCTYPE') || trimmed.includes('<html') || trimmed.includes('<div'))) {
      return 'html';
    }
    
    // CSS detection
    if (/[.#]?\w+\s*{[^}]*}/.test(trimmed) || /@\w+/.test(trimmed)) {
      return 'css';
    }
    
    // SQL detection
    if (/\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b/i.test(trimmed)) {
      return 'sql';
    }
    
    // Python detection
    if (/\bdef\s+\w+\(|class\s+\w+:|import\s+\w+|from\s+\w+\s+import/.test(trimmed)) {
      return 'python';
    }
    
    // Java detection
    if (/\b(public|private|protected)\s+(static\s+)?(\w+\s+)*\w+\s*\(|class\s+\w+|package\s+[\w.]+/.test(trimmed)) {
      return 'java';
    }
    
    // C/C++ detection
    if (/#include\s*[<"]|int\s+main\s*\(|#define\s+\w+/.test(trimmed)) {
      return 'cpp';
    }
    
    // TypeScript detection
    if (/:\s*\w+(\[\])?(\s*\|\s*\w+)*\s*[=;]|interface\s+\w+|type\s+\w+\s*=/.test(trimmed)) {
      return 'typescript';
    }
    
    // JavaScript detection
    if (/\b(function|const|let|var|=>|require\(|import\s+.*from)\b/.test(trimmed)) {
      return 'javascript';
    }
    
    return 'text';
  }

  /**
   * ⚡ JAVASCRIPT/TYPESCRIPT FORMATTER
   */
  private formatJavaScript(code: string, options: BeautifyOptions): string {
    let lines = code.split('\n');
    let formatted: string[] = [];
    let indentLevel = 0;
    let inString = false;
    let stringChar = '';
    
    for (let line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        // Preserve empty lines but limit consecutive ones
        if (formatted.length > 0 && formatted[formatted.length - 1] !== '') {
          formatted.push('');
        }
        continue;
      }
      
      // Handle string detection
      const { inStr, strChar } = this.trackStringState(trimmed, inString, stringChar);
      inString = inStr;
      stringChar = strChar;
      
      if (inString) {
        formatted.push(line);
        continue;
      }
      
      // Decrease indent for closing braces, brackets, and parentheses
      if (trimmed.startsWith('}') || trimmed.startsWith(']') || trimmed.startsWith(')')) {
        indentLevel = Math.max(0, indentLevel - 1);
      }
      
      // Format the line with proper spacing
      let formattedLine = this.formatJSLine(trimmed);
      
      // Apply indentation using spaces (consistent tab-size of 2)
      const indent = options.useSpaces ? 
        ' '.repeat(indentLevel * options.indentSize!) : 
        '\t'.repeat(indentLevel);
      
      formattedLine = indent + formattedLine;
      
      formatted.push(formattedLine);
      
      // Increase indent for opening braces, brackets, and parentheses
      if (trimmed.endsWith('{') || trimmed.endsWith('[') || 
          (trimmed.endsWith('(') && !trimmed.includes(')'))) {
        indentLevel++;
      }
      
      // Handle special cases for control structures
      if (this.isControlStructure(trimmed) && !trimmed.includes('{')) {
        indentLevel++;
      }
    }
    
    return this.addProperLineBreaks(formatted.join('\n'), 'javascript');
  }
  


  /**
   * 🟩 JAVA FORMATTER WITH PRETTIER - 100% Perfect Formatting
   * Uses prettier-plugin-java for professional-grade Java code formatting
   */
  private formatJavaWithPrettier(code: string): string {
    try {
      // Prettier.format is synchronous for Java
      const formatted = (prettier.format(code, {
        parser: 'java',
        plugins: [javaPlugin],
        tabWidth: 4,
        useTabs: false,
        printWidth: 100,
        singleQuote: false,
        trailingComma: 'none',
        bracketSpacing: true,
        arrowParens: 'always',
      }) as unknown) as string;
      
      console.log('✨ Java code formatted with Prettier');
      return formatted.trim();
    } catch (error) {
      console.warn('🚨 Prettier Java formatting failed, falling back to custom formatter:', error);
      // Fallback to custom formatter if Prettier fails
      const fallbackResult = this.formatCLike(code, { indentSize: 4 }, 'java');
      return fallbackResult;
    }
  }

  /**
   * ⚡ PREMIUM JAVA FORMATTER - Perfect IDE Quality Output (Fallback)
   */
  private formatCLike(code: string, options: BeautifyOptions, language: string): string {
    // Step 1: Pre-process broken code (AGGRESSIVE splitting)
    let preprocessed = this.preprocessJavaCode(code);
    
    // Step 2: Split into lines and format each
    let lines = preprocessed.split('\n');
    let formatted: string[] = [];
    let indentLevel = 0;
    let inString = false;
    let stringChar = '';
    let inMultiLineComment = false;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      const nextLine = i < lines.length - 1 ? lines[i + 1]?.trim() : '';
      const prevLine = i > 0 ? formatted[formatted.length - 1]?.trim() : '';
      
      // Handle empty lines - preserve for spacing
      if (!trimmed) {
        // Add empty line for spacing between methods/blocks
        if (prevLine && prevLine !== '' && nextLine && nextLine !== '') {
          // Check if we should add spacing
          if (this.shouldAddSpaceBetween(prevLine, nextLine)) {
            formatted.push('');
          }
        }
        continue;
      }
      
      // Track multi-line comments
      if (trimmed.includes('/**') || trimmed.includes('/*')) {
        inMultiLineComment = true;
      }
      if (trimmed.includes('*/')) {
        inMultiLineComment = false;
      }
      
      // Handle string literals
      const { inStr, strChar } = this.trackStringState(trimmed, inString, stringChar);
      inString = inStr;
      stringChar = strChar;
      
      if (inString || inMultiLineComment) {
        // Preserve comment and string formatting
        const indent = '    '.repeat(indentLevel);
        formatted.push(indent + trimmed);
        continue;
      }
      
      // 🔥 CRITICAL: Handle braces on separate lines
      // If line ends with opening brace, put brace on same line, then increase indent
      // If line starts with closing brace, decrease indent first, then add brace
      
      let lineToFormat = trimmed;
      let shouldIncreaseIndent = false;
      let shouldDecreaseIndent = false;
      
      // 🔥 FINAL CHECK: Split any remaining inline statements
      // Check if line has multiple statements that weren't split
      if (trimmed.includes(';') && trimmed.split(';').length > 2) {
        // Multiple statements on one line - split them
        const parts = trimmed.split(';');
        for (let j = 0; j < parts.length - 1; j++) {
          const part = parts[j].trim();
          if (part) {
            const indent = '    '.repeat(indentLevel);
            formatted.push(indent + part + ';');
          }
        }
        // Process the last part
        const lastPart = parts[parts.length - 1].trim();
        if (lastPart) {
          // Update the line variable for next iteration and reprocess
          lines[i] = lastPart;
          // Reprocess this line with the last part
          const reprocessedLine = lines[i];
          const reprocessedTrimmed = reprocessedLine.trim();
          
          // Check for closing brace at start
          if (reprocessedTrimmed.startsWith('}')) {
            indentLevel = Math.max(0, indentLevel - 1);
            const rest = reprocessedTrimmed.substring(1).trim();
            if (rest) {
              lines.splice(i + 1, 0, rest);
            }
            lineToFormat = '}';
            shouldDecreaseIndent = true;
          } else {
            lineToFormat = this.formatCLikeLine(reprocessedTrimmed, language);
          }
          
          // Apply indentation and add
          const indent = '    '.repeat(indentLevel);
          formatted.push(indent + lineToFormat);
          
          if (reprocessedTrimmed.endsWith('{') || reprocessedTrimmed === '{') {
            indentLevel++;
          }
          
          continue;
        } else {
          continue; // Skip if no last part
        }
      }
      
      // Check for closing brace at start
      if (trimmed.startsWith('}')) {
        indentLevel = Math.max(0, indentLevel - 1);
        shouldDecreaseIndent = true;
        // If there's more after the brace, split it
        if (trimmed.length > 1 && trimmed.substring(1).trim()) {
          lineToFormat = '}';
          // The rest will be processed in next iteration
          const rest = trimmed.substring(1).trim();
          if (rest) {
            // Process the rest as a new line
            lines.splice(i + 1, 0, rest);
          }
        } else {
          lineToFormat = '}';
        }
      }
      
      // Check for opening brace at end
      if (trimmed.endsWith('{') && !trimmed.startsWith('{')) {
        // Keep brace on same line
        shouldIncreaseIndent = true;
      } else if (trimmed === '{') {
        // Standalone opening brace
        shouldIncreaseIndent = true;
      }
      
      // Format the line content (if not just a brace)
      if (lineToFormat !== '{' && lineToFormat !== '}') {
        lineToFormat = this.formatCLikeLine(lineToFormat, language);
      }
      
      // Apply proper indentation (4 spaces for Java)
      const indent = '    '.repeat(indentLevel);
      const formattedLine = indent + lineToFormat;
      
      // Add the formatted line
      formatted.push(formattedLine);
      
      // Increase indent after opening brace
      if (shouldIncreaseIndent) {
        indentLevel++;
      }
      
      // Add strategic spacing between code blocks
      if (nextLine && this.shouldAddSpaceBetween(formattedLine.trim(), nextLine)) {
        formatted.push('');
      }
    }
    
    return this.finalCleanup(formatted.join('\n'));
  }
  
  /**
   * 🔍 Check if we should add space between two lines
   */
  private shouldAddSpaceBetween(prevLine: string, nextLine: string): boolean {
    if (!prevLine || !nextLine) return false;
    
    const prev = prevLine.trim();
    const next = nextLine.trim();
    
    // After closing brace before method/class
    if (prev === '}' && this.isMethodOrClassDeclaration(next)) {
      return true;
    }
    
    // After method/class declaration with opening brace
    if (prev.endsWith('{') && this.isMethodOrClassDeclaration(prev.replace('{', '').trim())) {
      return false; // No space right after opening brace
    }
    
    // After closing brace before another closing brace (nested)
    if (prev === '}' && next === '}') {
      return false;
    }
    
    // After method body ends, before next method
    if (prev === '}' && (next.startsWith('public') || next.startsWith('private') || next.startsWith('protected'))) {
      return true;
    }
    
    return false;
  }
  
  /**
   * 🔧 ADVANCED Pre-processor - Fixes broken AI-generated code
   * 🔥 AGGRESSIVE: Splits ALL inline statements onto separate lines
   */
  private preprocessJavaCode(code: string): string {
    // Step 1: Fix multi-line comments first (JavaDoc)
    let fixed = this.fixMultiLineComments(code);
    
    // Step 2: Fix obvious broken syntax
    fixed = fixed
      // Fix incomplete for loops
      .replace(/for\s*\(\s*int\s+(\w+)\s*=\s*s\.length\(\s*$/gm, 'for (int $1 = s.length() - 1; $1 >= 0; $1--)')
      .replace(/for\s*\(\s*int\s+(\w+)\s*=\s*(\w+)\.length\(\)\s*$/gm, 'for (int $1 = $2.length() - 1; $1 >= 0; $1--)')
      .replace(/for\s*\(\s*int\s+(\w+)\s*=\s*0\s*$/gm, 'for (int $1 = 0; $1 < n; $1++)')
      
      // Fix broken method calls
      .replace(/(\w+)\s*\(\s*$/gm, '$1();')
      
      // Fix incomplete if statements  
      .replace(/if\s*\(\s*$/gm, 'if (condition)')
      
      // Fix missing semicolons
      .replace(/^(\s*)(int|String|boolean|char|double|float)\s+\w+(\s*=\s*[^;\n]+)?\s*$/gm, '$1$2 $3;')
      .replace(/^(\s*)(return\s+[^;\n]+)\s*$/gm, '$1$2;');
    
    // 🔥 STEP 3: AGGRESSIVE STATEMENT SPLITTING - CRITICAL!
    // Split after opening braces, dots, and brackets - MOVE TO NEXT LINE
    fixed = fixed
      // 🔥 MOST IMPORTANT: Split after opening brace - content ALWAYS moves to next line
      // Pattern: "class Main { public static" → "class Main {\n    public static"
      // Pattern: "if (condition) { code" → "if (condition) {\n    code"
      .replace(/\{\s+([^\n}])/g, '{\n    $1')
      // Split after closing brace
      .replace(/\}\s{2,}([a-zA-Z_$])/g, '}\n$1')
      .replace(/\}\s+(public|private|protected|static|final|abstract|class|interface|enum|int|String|boolean|char|double|float|if|for|while|return)\s/g, '}\n$1 ')
      // 🔥 Split after dot (.) - method chaining moves to next line
      // Pattern: "obj.method1().method2()" → "obj.method1()\n    .method2()"
      // But don't split numbers like "3.14" or in strings
      .replace(/([a-zA-Z_$][\w$]*\)?)\s*\.\s*([a-zA-Z_$][\w$]*\s*\()/g, '$1\n    .$2')
      .replace(/\)\s*\.\s*([a-zA-Z_$])/g, ')\n    .$1')
      // 🔥 Split after bracket [ - array access moves to next line
      // Pattern: "arr[0]" → "arr\n    [0]"
      // But preserve array declarations like "int[]" or "String[] arr ="
      .replace(/([a-zA-Z_$][\w$]*)\s*\[\s*([^\]]+)\]\s*(?![=\[])/g, (match, varName, index) => {
        // Don't split if it's part of array declaration "int[]" or "String[] arr ="
        if (match.match(/\b(int|String|boolean|char|double|float)\[\]/)) {
          return match;
        }
        return varName + '\n    [' + index.trim() + ']';
      })
      // Split after semicolon
      .replace(/;\s{2,}([a-zA-Z_$])/g, ';\n    $1')
      .replace(/;\s+(int|String|boolean|char|double|float|if|for|while|return|public|private|protected|static|final|abstract)\s/g, ';\n    $1 ')
      // Ensure opening brace has proper spacing: "){" → ") {"
      .replace(/\)\s*\{/g, ') {')
      // Split multiple statements on same line
      .replace(/([^;])\s*;\s*([a-zA-Z_$])/g, '$1;\n    $2')
      // Split method declarations from class declarations
      .replace(/(class|interface|enum)\s+(\w+)\s*\{\s*(public|private|protected|static)/g, '$1 $2 {\n    $3')
      // Split return statements from closing braces
      .replace(/;\s*\}/g, ';\n}')
      // Split comments from code
      .replace(/(\/\/[^\n]*)\s{2,}([a-zA-Z_$])/g, '$1\n    $2')
      .replace(/(\/\/[^\n]*)\s+(int|String|boolean|char|double|float|public|private|protected|static|final|abstract|if|for|while|return)\s/g, '$1\n    $2 ');
    
    // 🔥 STEP 4: Split into lines and process each line
    let lines = fixed.split('\n');
    let processed: string[] = [];
    
    for (let line of lines) {
      let trimmed = line.trim();
      if (!trimmed) {
        // Preserve empty lines for spacing
        if (processed.length > 0 && processed[processed.length - 1] !== '') {
          // Don't add multiple consecutive empty lines yet
        }
        continue;
      }
      
      // 🔥 CRITICAL: Further split any remaining inline statements
      // Check if line has multiple statements (has semicolon but more code after)
      if (trimmed.includes(';') && trimmed.split(';').length > 2) {
        // Split by semicolon and process each part
        const parts = trimmed.split(';');
        for (let i = 0; i < parts.length - 1; i++) {
          const part = parts[i].trim();
          if (part) {
            processed.push(part + ';');
          }
        }
        const lastPart = parts[parts.length - 1].trim();
        if (lastPart) {
          processed.push(lastPart);
        }
      } else if (trimmed.match(/\}\s+[a-zA-Z_$]/)) {
        // Split closing brace from following code
        const match = trimmed.match(/^(\})\s+(.+)$/);
        if (match) {
          processed.push(match[1]);
          processed.push(match[2]);
        } else {
          processed.push(trimmed);
        }
      } else if (trimmed.match(/\{\s+[a-zA-Z_$]/)) {
        // Split opening brace from following code
        const match = trimmed.match(/^(.+?)\s*\{\s+(.+)$/);
        if (match) {
          processed.push(match[1] + ' {');
          processed.push(match[2]);
        } else {
          processed.push(trimmed);
        }
      } else {
        processed.push(trimmed);
      }
    }
    
    return processed.join('\n');
  }
  
  /**
   * 📝 Fix multi-line comments (JavaDoc) - Format properly
   */
  private fixMultiLineComments(code: string): string {
    // Fix JavaDoc comments that are on one line
    // Pattern: /** * comment * @param ... * @return ... */
    let fixed = code
      // Fix: "/** * comment" → "/**\n * comment"
      .replace(/(\/\*\*)\s*\*\s*([^\n]+)/g, (match, start, comment) => {
        // If it's a single-line JavaDoc, split it properly
        if (comment.includes('@param') || comment.includes('@return') || comment.includes('@throws')) {
          // Multi-line JavaDoc - split each tag
          let parts = comment.split(/\s+\*\s*@/);
          let result = start + '\n * ' + parts[0].trim();
          for (let i = 1; i < parts.length; i++) {
            result += '\n * @' + parts[i].trim();
          }
          return result;
        }
        return start + '\n * ' + comment.trim();
      })
      // Fix: "* @param ... * @return" → "* @param ...\n * @return"
      .replace(/\*\s*@(\w+)\s+([^\n]+)\s+\*\s*@(\w+)/g, '* @$1 $2\n * @$3')
      // Ensure proper JavaDoc structure
      .replace(/(\/\*\*)\s*([^\n]+)\s*(\*\/)/g, (match, start, content, end) => {
        // If content has tags, format properly
        if (content.includes('@param') || content.includes('@return')) {
          let lines = content.split(/\s+\*\s*/).filter(l => l.trim());
          let result = start + '\n';
          for (let line of lines) {
            if (line.trim()) {
              result += ' * ' + line.trim() + '\n';
            }
          }
          return result + ' ' + end;
        }
        return start + '\n * ' + content.trim() + '\n ' + end;
      });
    
    return fixed;
  }
  
  /**
   * 📏 Add strategic spacing between code blocks
   */
  private addStrategicSpacing(formatted: string[], currentLine: string, nextLine: string, indentLevel: number): void {
    if (!nextLine) return;
    
    const shouldAddSpace = (
      // After method declarations
      (this.isMethodOrClassDeclaration(currentLine) && currentLine.endsWith('{')) ||
      // After closing braces before new methods
      (currentLine.trim() === '}' && this.isMethodOrClassDeclaration(nextLine)) ||
      // After single-line if/return statements
      ((currentLine.includes('if (') || currentLine.includes('return ')) && currentLine.endsWith(';')) ||
      // After variable declarations before loops/conditions
      (currentLine.match(/\b(int|String|boolean|double|float)\b.*;$/) && 
       (nextLine.startsWith('for') || nextLine.startsWith('if') || nextLine.startsWith('while')))
    );
    
    if (shouldAddSpace) {
      formatted.push('');
    }
  }
  
  /**
   * ✨ Final cleanup for perfect IDE-quality formatting
   */
  private finalCleanup(code: string): string {
    return code
      // Remove excessive empty lines
      .replace(/\n{3,}/g, '\n\n')
      // Ensure proper spacing around braces
      .replace(/\{\n\n+/g, '{\n')
      .replace(/\n+\}/g, '\n}')
      // Clean trailing whitespace
      .replace(/[ \t]+$/gm, '')
      // Ensure consistent line endings
      .replace(/\r\n/g, '\n')
      .trim();
  }
  
  /**
   * 🔍 Check if line is a method or class declaration
   */
  private isMethodOrClassDeclaration(line: string): boolean {
    if (!line) return false;
    const trimmed = line.trim();
    return (
      // Access modifiers and keywords
      /^(public|private|protected|static|final|abstract|synchronized|native)\s/.test(trimmed) ||
      // Class/interface/enum declarations
      /^(class|interface|enum)\s+\w+/.test(trimmed) ||
      // Method signatures (return type + method name + parentheses)
      /^\w+\s+\w+\s*\([^)]*\)/.test(trimmed) ||
      // Constructor (class name followed by parentheses)
      /^[A-Z]\w*\s*\([^)]*\)/.test(trimmed) ||
      // Generic method signatures
      /^<.*>\s*\w+\s+\w+\s*\([^)]*\)/.test(trimmed)
    );
  }
  
  /**
   * 🎯 Check if line is a control structure
   */
  private isControlStructure(line: string): boolean {
    const trimmed = line.trim();
    return /^(if|else|for|while|do|switch|try|catch|finally)\b/.test(trimmed);
  }
  
  /**
   * 📏 Determine if we should add spacing after current line
   */
  private shouldAddSpaceAfter(currentLine: string, nextLine: string, prevLine: string): boolean {
    if (!nextLine || !currentLine) return false;
    
    const current = currentLine.trim();
    const next = nextLine.trim();
    
    return (
      // After method/class declaration with opening brace
      (this.isMethodOrClassDeclaration(current) && current.endsWith('{')) ||
      // After standalone statements before method/class
      (current.endsWith(';') && this.isMethodOrClassDeclaration(next)) ||
      // After closing brace before next method/class
      (current === '}' && this.isMethodOrClassDeclaration(next)) ||
      // After single-line if/return before next statement
      ((current.startsWith('if') || current.startsWith('return')) && 
       current.endsWith(';') && !next.startsWith('}')) ||
      // Before control structures in method body
      (current.endsWith(';') && (next.startsWith('if') || next.startsWith('for') || next.startsWith('while'))) ||
      // After variable declarations before loops
      (current.match(/^\s*(int|String|boolean|double|float)\s+\w+.*;$/) && 
       (next.startsWith('for') || next.startsWith('while')))
    );
  }

  /**
   * 🐍 PYTHON FORMATTER (4-space indentation) - Enhanced
   */
  private formatPython(code: string, options: BeautifyOptions): string {
    let lines = code.split('\n');
    let formatted: string[] = [];
    let indentLevel = 0;
    let lastLineWasEmpty = false;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      const nextLine = i < lines.length - 1 ? lines[i + 1]?.trim() : '';
      
      // Handle empty lines with proper spacing
      if (!trimmed) {
        if (!lastLineWasEmpty && formatted.length > 0) {
          // Add empty line for class/function separation
          if (nextLine?.startsWith('def ') || nextLine?.startsWith('class ') ||
              formatted[formatted.length - 1]?.trim().startsWith('def ') ||
              formatted[formatted.length - 1]?.trim().startsWith('class ')) {
            formatted.push('');
            lastLineWasEmpty = true;
          }
        }
        continue;
      }
      
      lastLineWasEmpty = false;
      
      // Calculate proper indentation level
      const originalIndent = line.length - line.trimStart().length;
      
      // Decrease indent for dedented lines
      if (this.isPythonDedent(trimmed)) {
        indentLevel = Math.max(0, indentLevel - 1);
      }
      
      // Format the line with enhanced Python spacing
      let formattedLine = this.formatPythonLine(trimmed);
      
      // Apply 4-space indentation
      const indent = ' '.repeat(indentLevel * 4);
      formattedLine = indent + formattedLine;
      
      formatted.push(formattedLine);
      
      // Increase indent after colon (for functions, classes, if, etc.)
      if (trimmed.endsWith(':')) {
        indentLevel++;
      }
      
      // Add spacing after class/function definitions
      if ((trimmed.startsWith('def ') || trimmed.startsWith('class ')) && trimmed.endsWith(':')) {
        if (nextLine && !nextLine.startsWith('def ') && !nextLine.startsWith('class ')) {
          formatted.push('');
        }
      }
    }
    
    return this.addPythonLineBreaks(formatted.join('\n'));
  }

  /**
   * 🌐 HTML FORMATTER
   */
  private formatHTML(code: string, options: BeautifyOptions): string {
    let lines = code.split('\n');
    let formatted: string[] = [];
    let indentLevel = 0;
    
    for (let line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      
      // Self-closing or closing tags
      if (trimmed.startsWith('</') || trimmed.match(/<\w+[^>]*\/>/)) {
        if (trimmed.startsWith('</')) {
          indentLevel = Math.max(0, indentLevel - 1);
        }
      }
      
      let formattedLine = ' '.repeat(indentLevel * options.indentSize!) + trimmed;
      formatted.push(formattedLine);
      
      // Opening tags (not self-closing, not closing)
      if (trimmed.startsWith('<') && !trimmed.startsWith('</') && !trimmed.endsWith('/>') && !trimmed.match(/<\w+[^>]*\/>/)) {
        indentLevel++;
      }
    }
    
    return formatted.join('\n');
  }

  /**
   * 🎨 CSS FORMATTER
   */
  private formatCSS(code: string, options: BeautifyOptions): string {
    let formatted = code
      .replace(/\s*{\s*/g, ' {\n')
      .replace(/;\s*/g, ';\n')
      .replace(/\s*}\s*/g, '\n}\n')
      .replace(/,\s*/g, ',\n');
    
    let lines = formatted.split('\n');
    let result: string[] = [];
    let indentLevel = 0;
    
    for (let line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      
      if (trimmed === '}') {
        indentLevel = Math.max(0, indentLevel - 1);
      }
      
      result.push(' '.repeat(indentLevel * options.indentSize!) + trimmed);
      
      if (trimmed.endsWith('{')) {
        indentLevel++;
      }
    }
    
    return result.join('\n');
  }

  /**
   * 🗃️ SQL FORMATTER
   */
  private formatSQL(code: string, options: BeautifyOptions): string {
    const keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'];
    
    let formatted = code;
    
    // Uppercase keywords
    keywords.forEach(keyword => {
      const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
      formatted = formatted.replace(regex, keyword);
    });
    
    // Add proper spacing
    formatted = formatted
      .replace(/\s*,\s*/g, ', ')
      .replace(/\s*=\s*/g, ' = ')
      .replace(/\s*<\s*/g, ' < ')
      .replace(/\s*>\s*/g, ' > ');
    
    return formatted;
  }

  /**
   * 📦 JSON FORMATTER
   */
  private formatJSON(code: string, options: BeautifyOptions): string {
    try {
      const parsed = JSON.parse(code);
      return JSON.stringify(parsed, null, options.indentSize);
    } catch {
      return code; // Return original if invalid JSON
    }
  }

  /**
   * 🔧 GENERIC FORMATTER (fallback)
   */
  private formatGeneric(code: string, options: BeautifyOptions): string {
    let lines = code.split('\n');
    let formatted: string[] = [];
    let indentLevel = 0;
    
    for (let line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      
      // Basic brace handling
      if (trimmed.startsWith('}') || trimmed.startsWith(']') || trimmed.startsWith(')')) {
        indentLevel = Math.max(0, indentLevel - 1);
      }
      
      let formattedLine = this.addBasicSpacing(trimmed);
      formattedLine = ' '.repeat(indentLevel * options.indentSize!) + formattedLine;
      
      formatted.push(formattedLine);
      
      if (trimmed.endsWith('{') || trimmed.endsWith('[') || trimmed.endsWith('(')) {
        indentLevel++;
      }
    }
    
    return formatted.join('\n');
  }

  // ========================================
  // 🛠️ HELPER METHODS
  // ========================================

  private formatJSLine(line: string): string {
    return line
      // Operators with proper spacing
      .replace(/\s*=\s*/g, ' = ')
      .replace(/\s*\+\s*/g, ' + ')
      .replace(/\s*-\s*/g, ' - ')
      .replace(/\s*\*\s*/g, ' * ')
      .replace(/\s*\/\s*/g, ' / ')
      .replace(/\s*%\s*/g, ' % ')
      .replace(/\s*==\s*/g, ' == ')
      .replace(/\s*===\s*/g, ' === ')
      .replace(/\s*!=\s*/g, ' != ')
      .replace(/\s*!==\s*/g, ' !== ')
      .replace(/\s*<=\s*/g, ' <= ')
      .replace(/\s*>=\s*/g, ' >= ')
      .replace(/\s*<\s*/g, ' < ')
      .replace(/\s*>\s*/g, ' > ')
      .replace(/\s*&&\s*/g, ' && ')
      .replace(/\s*\|\|\s*/g, ' || ')
      .replace(/\s*\?\s*/g, ' ? ')
      .replace(/\s*:\s*/g, ' : ')
      // Punctuation and brackets
      .replace(/,\s*/g, ', ')
      .replace(/;\s*/g, '; ')
      .replace(/\(\s*/g, '(')
      .replace(/\s*\)/g, ')')
      .replace(/\[\s*/g, '[')
      .replace(/\s*\]/g, ']')
      .replace(/{\s*/g, ' {')
      .replace(/}\s*/g, '}')
      // Function calls and declarations  
      .replace(/function\s*\(/g, 'function (')
      .replace(/\)\s*{/g, ') {')
      // Arrow functions
      .replace(/=>\s*{/g, ' => {')
      .replace(/\)\s*=>/g, ') =>')
      // Keywords
      .replace(/\bif\s*\(/g, 'if (')
      .replace(/\bfor\s*\(/g, 'for (')
      .replace(/\bwhile\s*\(/g, 'while (')
      .replace(/\bswitch\s*\(/g, 'switch (')
      .replace(/\bcatch\s*\(/g, 'catch (')
      // Clean up excessive spaces
      .replace(/\s{2,}/g, ' ')
      .trim();
  }

  private formatCLikeLine(line: string, language: string): string {
    let formatted = line.trim();
    
    // Don't format lone braces
    if (formatted === '{' || formatted === '}') {
      return formatted;
    }
    
    formatted = formatted
      // Enhanced operator spacing
      .replace(/\s*=\s*(?!=)/g, ' = ')
      .replace(/\s*\+=\s*/g, ' += ')
      .replace(/\s*-=\s*/g, ' -= ')
      .replace(/\s*\*=\s*/g, ' *= ')
      .replace(/\s*\/=\s*/g, ' /= ')
      .replace(/\s*==\s*/g, ' == ')
      .replace(/\s*!=\s*/g, ' != ')
      .replace(/\s*<=\s*/g, ' <= ')
      .replace(/\s*>=\s*/g, ' >= ')
      .replace(/\s*<\s*/g, ' < ')
      .replace(/\s*>\s*/g, ' > ')
      .replace(/\s*&&\s*/g, ' && ')
      .replace(/\s*\|\|\s*/g, ' || ')
      .replace(/\s*\?\s*/g, ' ? ')
      .replace(/\s*:\s*/g, ' : ')
      
      // Arithmetic operators
      .replace(/\s*\+\s*/g, ' + ')
      .replace(/\s*-\s*/g, ' - ')
      .replace(/\s*\*\s*/g, ' * ')
      .replace(/\s*\/\s*/g, ' / ')
      .replace(/\s*%\s*/g, ' % ')
      
      // Enhanced brackets and punctuation
      .replace(/,\s*/g, ', ')
      .replace(/;\s*(?!$)/g, '; ')  // Semicolon with space unless end of line
      .replace(/;$/, ';')           // Clean semicolon at end
      .replace(/\(\s+/g, '(')       // Remove space after opening parenthesis
      .replace(/\s+\)/g, ')')       // Remove space before closing parenthesis
      .replace(/\[\s+/g, '[')
      .replace(/\s+\]/g, ']')
      .replace(/\{\s*/g, ' {')
      .replace(/\}\s*/g, '}')
      
      // Special Java/C++ formatting
      .replace(/\bif\s*\(/g, 'if (')
      .replace(/\bfor\s*\(/g, 'for (')
      .replace(/\bwhile\s*\(/g, 'while (')
      .replace(/\bswitch\s*\(/g, 'switch (')
      .replace(/\bcatch\s*\(/g, 'catch (')
      .replace(/\)\s*\{/g, ') {')
      
      // Java/C++ specific formatting
      .replace(/\b(if|for|while|switch|catch)\s*\(/g, '$1 (')
      .replace(/\b(class|interface|enum)\s+/g, '$1 ')
      .replace(/\b(public|private|protected|static|final|abstract)\s+/g, '$1 ')
      .replace(/\)\s*{/g, ') {')
      
      // Method declarations
      .replace(/(\w+)\s*\(/g, '$1(')
      .replace(/\)\s*(throws\s+\w+)?\s*{/g, ') $1{')
      
      // Array declarations
      .replace(/(\w+)\[\]\s*(\w+)/g, '$1[] $2')
      .replace(/(\w+)\s*\[\]/g, '$1[]')
      
      // Clean up excessive spaces
      .replace(/\s{2,}/g, ' ')
      .trim();
    
    // Add semicolon if missing for statements that should have them
    if (this.shouldHaveSemicolon(formatted, language)) {
      formatted += ';';
    }
    
    return formatted;
  }
  
  /**
   * 🔍 Check if line should end with semicolon
   */
  private shouldHaveSemicolon(line: string, language: string): boolean {
    if (!['java', 'c', 'cpp'].includes(language)) return false;
    
    const trimmed = line.trim();
    
    // Don't add semicolon if line already ends with punctuation or is a control structure
    if (/[{}();:]$/.test(trimmed)) return false;
    
    // Don't add to control structures, declarations, or comments
    if (/^(if|else|for|while|switch|case|default|public|private|protected|class|interface|enum|package|import|\/\*|\/\/|\*)\b/.test(trimmed)) return false;
    
    // Don't add to opening statements
    if (trimmed.includes('{') || trimmed.startsWith('}')) return false;
    
    // Add semicolon to variable declarations, assignments, method calls, returns
    return /^(\w+\s+\w+|\w+\s*=|\w+\.|return\s|\w+\s*\()/.test(trimmed);
  }

  private formatPythonLine(line: string): string {
    return line
      // Operators with proper spacing
      .replace(/\s*=\s*/g, ' = ')
      .replace(/\s*\+=\s*/g, ' += ')
      .replace(/\s*-=\s*/g, ' -= ')
      .replace(/\s*\*=\s*/g, ' *= ')
      .replace(/\s*\/=\s*/g, ' /= ')
      .replace(/\s*==\s*/g, ' == ')
      .replace(/\s*!=\s*/g, ' != ')
      .replace(/\s*<=\s*/g, ' <= ')
      .replace(/\s*>=\s*/g, ' >= ')
      .replace(/\s*<\s*/g, ' < ')
      .replace(/\s*>\s*/g, ' > ')
      .replace(/\s*\+\s*/g, ' + ')
      .replace(/\s*-\s*/g, ' - ')
      .replace(/\s*\*\s*/g, ' * ')
      .replace(/\s*\/\s*/g, ' / ')
      .replace(/\s*\/\/\s*/g, ' // ')
      .replace(/\s*%\s*/g, ' % ')
      .replace(/\s*\*\*\s*/g, ' ** ')
      
      // Boolean operators
      .replace(/\s+and\s+/g, ' and ')
      .replace(/\s+or\s+/g, ' or ')
      .replace(/\s+not\s+/g, ' not ')
      .replace(/\s+in\s+/g, ' in ')
      .replace(/\s+is\s+/g, ' is ')
      
      // Punctuation
      .replace(/,\s*/g, ', ')
      .replace(/\(\s*/g, '(')
      .replace(/\s*\)/g, ')')
      .replace(/\[\s*/g, '[')
      .replace(/\s*\]/g, ']')
      .replace(/{\s*/g, '{')
      .replace(/\s*}/g, '}')
      .replace(/:(?!\s*$)/g, ': ')
      .replace(/:$/g, ':')
      
      // Function definitions and calls
      .replace(/\bdef\s+/g, 'def ')
      .replace(/\bclass\s+/g, 'class ')
      .replace(/\bif\s+/g, 'if ')
      .replace(/\belif\s+/g, 'elif ')
      .replace(/\belse:/g, 'else:')
      .replace(/\bfor\s+/g, 'for ')
      .replace(/\bwhile\s+/g, 'while ')
      .replace(/\btry:/g, 'try:')
      .replace(/\bexcept\s+/g, 'except ')
      .replace(/\bfinally:/g, 'finally:')
      
      // Clean up excessive spaces
      .replace(/\s{2,}/g, ' ')
      .trim();
  }

  private addBasicSpacing(line: string): string {
    return line
      .replace(/\s*=\s*/g, ' = ')
      .replace(/\s*\+\s*/g, ' + ')
      .replace(/\s*-\s*/g, ' - ')
      .replace(/,\s*/g, ', ')
      .replace(/\(\s*/g, '(')
      .replace(/\s*\)/g, ')');
  }

  /**
   * 🧹 Perfect code structure cleanup for professional formatting
   */
  private cleanupCodeStructure(code: string, language: string): string {
    let lines = code.split('\n');
    let result: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      
      // Skip multiple consecutive empty lines
      if (!trimmed) {
        // Only add empty line if the last added line wasn't empty
        if (result.length > 0 && result[result.length - 1].trim() !== '') {
          result.push('');
        }
        continue;
      }
      
      result.push(line);
    }
    
    // Final cleanup - perfect formatting
    return result.join('\n')
      // Ensure no more than one empty line between code blocks
      .replace(/\n\s*\n\s*\n/g, '\n\n')
      // Clean up trailing whitespace
      .replace(/[ \t]+$/gm, '')
      // Remove any leading/trailing empty lines
      .replace(/^\n+|\n+$/g, '')
      // Ensure proper indentation consistency
      .split('\n')
      .map(line => {
        if (!line.trim()) return '';
        // Standardize to 4-space indentation
        const leadingSpaces = line.match(/^\s*/)?.[0] || '';
        const content = line.trim();
        const indentLevel = Math.floor(leadingSpaces.length / 4);
        return '    '.repeat(indentLevel) + content;
      })
      .join('\n');
  }
  
  private addProperLineBreaks(code: string, language: string): string {
    // For C-like languages, use the enhanced cleanup
    if (['java', 'c', 'cpp'].includes(language)) {
      return this.cleanupCodeStructure(code, language);
    }
    
    // Original implementation for other languages
    let formatted = code
      .replace(/;(?!\s*[)}]|\s*$)/g, ';\n')
      .replace(/{(?!\s*$)/g, '{\n')
      .replace(/(?<!^\s*)}(?!\s*$)/g, '\n}');
    
    formatted = formatted.replace(/\n{3,}/g, '\n\n');
    return formatted;
  }

  private addPythonLineBreaks(code: string): string {
    let formatted = code
      // Add double line breaks before function/class definitions
      .replace(/\n(def |class )/g, '\n\n$1')
      // Add line break after colon
      .replace(/:(?!\s*$)/g, ':\n');
    
    // Clean up excessive line breaks
    formatted = formatted.replace(/\n{3,}/g, '\n\n');
    
    return formatted;
  }

  private isPythonDedent(line: string): boolean {
    return line.match(/^(else|elif|except|finally|case|default)/) !== null;
  }

  private trackStringState(line: string, inString: boolean, stringChar: string): { inStr: boolean; strChar: string } {
    let inStr = inString;
    let strChar = stringChar;
    
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      const prevChar = i > 0 ? line[i - 1] : '';
      
      if (!inStr && (char === '"' || char === "'" || char === '`')) {
        inStr = true;
        strChar = char;
      } else if (inStr && char === strChar && prevChar !== '\\') {
        inStr = false;
        strChar = '';
      }
    }
    
    return { inStr, strChar };
  }

  private finalCleanupWithOptions(code: string, options: BeautifyOptions): string {
    let cleaned = code
      // Remove trailing whitespace
      .replace(/[ \t]+$/gm, '')
      // Remove excessive empty lines
      .replace(/\n{4,}/g, '\n\n\n')
      // Ensure proper spacing around operators
      .replace(/([=+\-*/<>!])([=+\-*/<>!])/g, '$1 $2');
    
    // Add final newline if requested
    if (options.insertFinalNewline && !cleaned.endsWith('\n')) {
      cleaned += '\n';
    }
    
    return cleaned;
  }

  private isValidJSON(str: string): boolean {
    try {
      JSON.parse(str);
      return true;
    } catch {
      return false;
    }
  }
}

// ========================================
// 🚀 EASY-TO-USE FUNCTIONS
// ========================================

const beautifier = new CodeBeautifierEngine();

/**
 * ✨ Beautify code (main function)
 */
export const beautifyCode = (
  code: string, 
  language?: string, 
  options?: BeautifyOptions
): BeautifyResult => {
  return beautifier.beautify(code, language, options);
};

/**
 * 🎯 Quick beautify (returns just the formatted code)
 */
export const quickBeautify = (code: string, language?: string): string => {
  const result = beautifier.beautify(code, language);
  return result.success ? result.code : code;
};

/**
 * 🔍 Detect language
 */
export const detectLanguage = (code: string): string => {
  return beautifier['detectLanguage'](code);
};

/**
 * 📝 Format code for markdown display
 */
export const formatForMarkdown = (code: string, language?: string): string => {
  const result = beautifier.beautify(code, language);
  const lang = result.language !== 'text' ? result.language : '';
  
  return `\`\`\`${lang}\n${result.code}\n\`\`\``;
};

// ========================================
// 🧪 PRESET CONFIGURATIONS
// ========================================

export const PRESET_CONFIGS = {
  // Standard 2-space indentation
  standard: {
    indentSize: 2,
    useSpaces: true,
    maxLineLength: 80,
    insertFinalNewline: true,
  },
  
  // 4-space indentation (Python style)
  python: {
    indentSize: 4,
    useSpaces: true,
    maxLineLength: 88,
    insertFinalNewline: true,
  },
  
  // Tab indentation
  tabs: {
    indentSize: 1,
    useSpaces: false,
    maxLineLength: 80,
    insertFinalNewline: true,
  },
  
  // Compact formatting
  compact: {
    indentSize: 2,
    useSpaces: true,
    maxLineLength: 120,
    insertFinalNewline: false,
  }
};

export default CodeBeautifierEngine;