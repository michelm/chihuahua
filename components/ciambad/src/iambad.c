
#include <stdio.h>
#include <stdlib.h>
#include <leaking.h>

int main(int argc, char* argv[]) {
	int i;
	char s[5];
	char c;
	char *t;

	printf("start\n");

	for(i=0; i < 6; i++) {
		s[i] = 0;
	}

	s[c] = 4;

	while(1) {
		leaking();
		c++;
		s[c] = 256;
	}

	t = (char*)calloc(4, sizeof(char));
	t[164] = 7; // array out of bound (runtime array size)
	t[5] = 8; // array out of bound (runtime array size)

	printf("done\n");
	return EXIT_SUCCESS;
}