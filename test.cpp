#include <bits/stdc++.h>
#define int long long
#define pb emplace_back
using namespace std;

bool isPrim(int n) {
	if(n < 2) return 0;
	if(n == 2) return 1;
	if(n%2==0) return 0;
	for(int i = 3; i*i <= n; i+= 2) {
		if(n%i == 0) return 0;
	}
	return 1;
}

signed main() {
	
	int n;
	cin >> n;
	vector<int> v;
	set<int> st;
	while(n--) {
		int a;
		cin >> a;
		a++;
		v.push_back(a);
		st.insert(a);
		while(!isPrim(a)) {
			a++;
		} 
		cout << a << '\n';
	}
	return 0;
}