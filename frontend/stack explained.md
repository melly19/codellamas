
## Frontend Overview

This is a **VS Code extension** that generates Java code with intentional "code smells" for educational purposes.

### File Breakdown:

**package.json** - Extension manifest defining commands (`helloWorld`, `submitCode`), activity bar view (`codellamas_activityView`), and dependencies.

**extension.ts** - Entry point that registers:
- Activity sidebar provider
- Submit code button (status bar + editor title)
- Hello World command

**activityWebviewProvider.ts** - Core UI logic:
- **Main view**: Shows "Generate Questions" button
- **Generator panel**: Contains checkboxes for code smells and topic input
- **"Generate" button handler** (line 239): Sends `{type: "submit", topic, smells}` to backend at `http://localhost:8000/generate`
- **Response parsing** (line 31-36): Receives AI-generated Java code from backend and passes to `saveToSpringBootProject()`

**springBootSaver.ts** - Saves generated code to workspace:
- Finds Spring Boot main class
- Extracts package name
- Creates `.java` file in `src/main/java/<package>/<ClassName>.java`

### Key Flow:
1. **UI Design**: HTML strings in `getHtml()` and `getGeneratorHtml()` methods (activityWebviewProvider.ts)
2. **Button Handler**: `submit()` function posts message ([line 239](frontend/src/activityWebviewProvider.ts#L239))
3. **Backend Call**: `fetchAiQuestionsFromBackend()` posts to `/generate` endpoint ([line 46](frontend/src/activityWebviewProvider.ts#L46))
4. **Output Parsing**: Backend returns `{questions: string}` containing Java code ([line 56](frontend/src/activityWebviewProvider.ts#L56))
5. **File Creation**: `saveToSpringBootProject()` writes to workspace (springBootSaver.ts)