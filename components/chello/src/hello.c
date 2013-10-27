
#include <stdio.h>
#include <stdlib.h>
#include <hello.h>

int main(int argc, char* argv[])
{
	return say_hello();
}

int say_hello()
{
	printf("Hello! (version %s)\n", HELLO_VERSION);
	return EXIT_SUCCESS;
}
