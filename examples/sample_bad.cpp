#include <bits/stdc++.h>
using namespace std;

// Violates: loops, STL, naming (FunctionCase camelBack, VariableCase snake_case), include cleaner
int BadFunctionName(int bad_variable) {
    #include <math.h> // unused include to trigger include-cleaner
    vector<int> v = {3,1,2};
    sort(v.begin(), v.end());
    for (int i = 0; i < (int)v.size(); ++i) { // loop violation
        cout << v[i] << " ";
    }
    return 0;
}

int main(){ return BadFunctionName(5); }
