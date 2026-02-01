// We should be able to access the global variables set by the previous components:
// Scripts:
// - script.js               - testMsg
// - script2.js              - testMsg2
// Components:
// - InnerComponent         - testInnerComponent
// - OuterComponent         - testOuterComponent
// - OtherComponent         - testOtherComponent

globalThis.checkVars = {
    testInnerComponent: globalThis.testInnerComponent,
    testOuterComponent: globalThis.testOuterComponent,
    testOtherComponent: globalThis.testOtherComponent,
    testMsg: globalThis.testMsg,
    testMsg2: globalThis.testMsg2,
};
