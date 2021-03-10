// Example modified from https://www.geeksforgeeks.org/multiple-inheritance-in-c/
class Person { 
   // Data members of person  
    public{ 
        Person(int x)  { printf("Person::Person(int ) called");   } 
    };
}; 
  
class Faculty <- public Person { 
   // data members of Faculty 
    public{
        Faculty(int x):Person(x)   { 
        printf("Faculty::Faculty(int ) called"); 
        }
    }; 
}; 
  
class Student <- public Person { 
   // data members of Student 
    public{ 
        Student(int x)<-Person(x) { 
            printf("Student::Student(int ) called\n"); 
        } 
    };
}; 
  
class TA <- public Faculty, public Student  { 
    public{
        TA(int x)<-Student(x), Faculty(x)   { 
            printf("TA::TA(int ) called\n"); 
        } 
    };
}; 
  
int main()  { 
    class TA ta1(30); 
} 