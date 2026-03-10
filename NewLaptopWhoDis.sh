#!/bin/bash

r() { tr -dc 'A-Z0-9' </dev/urandom | head -c"$1"; }

randname(){
names=(Jennifer Michael Amanda Christopher Jessica Jason Melissa David Sarah James Heather Matthew Nicole Joshua Amy John Elizabeth Robert Michelle Joseph Kimberly Daniel Angela Brian Stephanie Justin Tiffany William Christina Ryan Lisa Eric Rebecca Nicholas Crystal Jeremy Kelly Andrew Erin Timothy Laura Jonathan Amber Adam Rachel Kevin Jamie Anthony Mary Thomas April Richard Sara Jeffrey Andrea Steven Shannon Charles Megan Brandon Emily Mark Julie Benjamin Danielle Scott Erica Aaron Katherine Paul Maria Nathan Kristin Travis Lauren Patrick Kristen Chad Ashley Stephen Christine Kenneth Brandy Gregory Tara Jacob Katie Dustin Monica Jesse Carrie Jose Alicia Shawn Courtney Sean Misty Bryan Kathryn Derek Patricia Bradley Holly Edward Stacy Donald Karen Samuel Anna Peter Tracy Keith Brooke Kyle Samantha Ronald Allison Juan Melanie George Leslie Jared Susan Douglas Brandi Gary Cynthia Erik Natalie Phillip Jill Raymond Dawn Joel Dana Corey Vanessa Shane Veronica Larry Lindsay Marcus Tina Zachary Kristina Craig Stacey Derrick Wendy Todd Lori Jeremiah Catherine Antonio Kristy Carlos Heidi Shaun Sandra Dennis Jacqueline Frank Kathleen Philip Christy Cory Leah Brent Valerie Gabriel Pamela Nathaniel Erika Randy Tanya Luis Natasha Curtis Katrina Jeffery Lindsey Alexander Melinda Russell Monique Casey Teresa Jerry Denise Wesley Tammy Brett Tonya Luke Julia Lucas Candice Seth Gina Billy Alison Terry Nichole Mario Victoria Carl Theresa Ian Margaret Jamie Beth Troy Renee Victor Tamara Tony Robin Bobby Linda Jesus Nancy Vincent Anne Alan Sabrina Johnny Meghan Tyler Brenda Adrian Jaime Brad Jenny Ricardo Diana Christian Cheryl Marc Barbara Danny Krista Rodney Kristi Ricky Latoya Martin Bethany Allen Michele Lee Kelli Jimmy Kara Jon Miranda Miguel Sharon Lawrence Tasha Willie Mindy Clinton Mandy Micheal Molly Andre Candace Roger Casey Henry Ann Randall Colleen Walter Cassandra Kristopher Suzanne Jorge Meredith Joe Latasha Jay Rachael Albert Regina Cody Donna Manuel Marie Roberto Deborah Wayne Carolyn Arthur Nina Gerald Deanna Jermaine Cindy Isaac Alisha Lance Bridget Louis Carla Roy Kendra Francisco Desiree Trevor Tabitha Alex Yolanda Bruce Kari Jack Summer Evan Virginia Jordan Trisha Frederick Rebekah Maurice Joanna Darren Felicia Mitchell Joy Ruben Bonnie Reginald Jodi Darrell Jaclyn Jaime Angel Hector Adrienne Omar Jillian Jonathon Janet Angel Paula Ronnie Aimee Johnathan Ebony Barry)
apple=(MacBook-Pro MacBook-Air MacBook iMac iMac-Pro Mac-mini Mac-Studio iPhone iPhone-Pro iPhone-Pro-Max)
android=(android Pixel Galaxy Galaxy-S Galaxy-Note OnePlus Redmi)

case $((RANDOM%4)) in
0)
  d=${apple[RANDOM%${#apple[@]}]}
  if ((RANDOM%2)); then
    echo "${names[RANDOM%${#names[@]}]}'s-$d";
    else echo "$d";
  fi
;;
1)
  if ((RANDOM%2));
    then echo "DESKTOP-$(r 7)";
    else echo "LAPTOP-$(r 7)";
  fi
;;
3)
  a=${android[RANDOM%${#android[@]}]}
  echo "$a-$((RANDOM%100))"
;;
esac
}

newname="$(randname)"
interface=$(ip -o link show up | awk -F': ' '/BROADCAST/ {print $2}')
local_ip() { ip -4 addr show "$interface" | awk '/inet / {print $2}' | cut -d/ -f1; }

echo "Current IP: $(local_ip)"
echo "Current MAC: $(ip link show "$interface" | awk '/link\/ether/ {print $2}')"

sudo ip link set dev "$interface" down

sudo hostnamectl set-hostname "$newname" --static
echo "Set hostname to $newname"

sudo macchanger -r "$interface" | grep New | sed 's/.\{1\}$//'

sudo ip link set dev "$interface" up

echo "New IP: $(local_ip)"

sleep 4

ping -c 4 -W 4 cloudflare.com
