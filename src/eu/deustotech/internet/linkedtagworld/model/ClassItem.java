package eu.deustotech.internet.linkedtagworld.model;

import java.util.ArrayList;
import java.util.List;

public class ClassItem {
	private String identifier = "";
	private String javaClass = "";
	private String ontologyClass = "";
	private List<PropertyItem> propertyItems = new ArrayList<PropertyItem>();
	
	public String getIdentifier() {
		return identifier;
	}
	public String getJavaClass() {
		return javaClass;
	}
	public String getOntologyClass() {
		return ontologyClass;
	}
	public List<PropertyItem> getPropertyItems() {
		return propertyItems;
	}
	public void setIdentifier(String identifier) {
		this.identifier = identifier;
	}
	public void setJavaClass(String javaClass) {
		this.javaClass = javaClass;
	}
	public void setOntologyClass(String ontologyClass) {
		this.ontologyClass = ontologyClass;
	}
	public void setPropertyItems(List<PropertyItem> propertyItems) {
		this.propertyItems = propertyItems;
	}
	
	public boolean validate() {
		if (this.ontologyClass == "") {
			return false;
		}
		return true;
	}
	
	@Override 
	public String toString() {
		StringBuilder result = new StringBuilder();
	    String NEW_LINE = System.getProperty("line.separator");

	    result.append(this.getClass().getName() + " Object {" + NEW_LINE);
	    if (identifier != "")
	    	result.append(" Identifier: " + identifier + NEW_LINE);
	    result.append(" Java Class: " + javaClass + NEW_LINE);
	    result.append(" Ontology Class: " + ontologyClass + NEW_LINE);
	    for (PropertyItem item : propertyItems) {
	    	result.append(item.toString() + NEW_LINE);
	    }
	    
		return result.toString();		
	}
	
}
