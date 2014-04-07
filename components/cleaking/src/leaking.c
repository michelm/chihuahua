#include "stdlib.h"
#include <leaking.h>

void leaking() {
	char* c;
	c = (char*)calloc(15, sizeof(*c));
}
