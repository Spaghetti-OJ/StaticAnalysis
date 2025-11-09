// test_stl.cpp - 測試 STL 禁用檢查
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

int main() {
    // 會被檢測到的 STL 使用
    std::vector<int> numbers = {1, 2, 3, 4, 5};
    std::string name = "Hello";
    
    std::cout << "Testing STL" << std::endl;
    
    std::sort(numbers.begin(), numbers.end());
    
    return 0;
}
