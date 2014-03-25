
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <hello.h>

int main(int argc, char* argv[])
{
	char buf[1024];

	say_hello();

	printf("The current directory is: %s\n", getcwd(buf, sizeof(buf)));
	return EXIT_SUCCESS;
}

void say_hello()
{
	printf("Hello! (version %s)\n", HELLO_VERSION);
}
