// This should work
class Person { 
   // Data members of person 
    private{
        long aadhar_number;
    };  
    private{
        char* name;
    }; 
    public{ 
        char * returnName()  { return this->name;} 
    };
}; 
  
class Faculty <- public Person { 
   // data members of Faculty
    protected{
        long employeeID;
    };  
    public{
        long getEmployeeID(){ 
         return this->employeeID; 
        }
    }; 
}; 
  
class Student <- public Person { 
   // data members of Student 
   private {
       long rollNo;
   };
    public{ 
        long getRollNo() { 
            return this->rollNo; 
        } 
    };
}; 
  
class TA <- public Faculty, public Student  {

    private{
        char** courses;
        int maxSize =  1024;
        int numCourses;
    }; 
    public{
        void printCourses(){ 
            int i;
            for(i=0; i<this->numCourses;i++)
                printf("%s", this->courses[i]); 
        }

    };
}; 
  
int main()  { 
    class TA ta1;
    ta1.printCourses(); 
} 