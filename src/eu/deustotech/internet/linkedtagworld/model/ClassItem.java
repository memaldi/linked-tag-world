package eu.deustotech.internet.linkedtagworld.model;

import java.util.ArrayList;
import java.util.List;

/**
 * Representation of an entity in LinkedTagWorld.
 * @author jon
 *
 */
public class ClassItem {
	private String identifier = "";
	private String javaClass = "";
	private String ontologyClass = "";
	private List<PropertyItem> propertyItems = new ArrayList<PropertyItem>();
	
	/**
	 * Returns the identifier of the class.
	 * @return the identifier of the class.
	 */
	public String getIdentifier() {
		return identifier;
	}
	
	/**
	 * Returns the Java Class which represents the entity.
	 * @return the Java Class of the entity.
	 */
	public String getJavaClass() {
		return javaClass;
	}
	
	/**
	 * Returns the OWL Class which represents the entity.
	 * @return the OWL Class of the entity.
	 */
	public String getOntologyClass() {
		return ontologyClass;
	}
	
	/**
	 * Returns the properties of the entity.
	 * @return list of properties of the entity.
	 */
	public List<PropertyItem> getPropertyItems() {
		return propertyItems;
	}
	
	/**
	 * Sets the identifier of the entity.
	 * @param identifier the identifier of the entity.
	 */
	public void setIdentifier(String identifier) {
		this.identifier = identifier;
	}
	
	/**
	 * Sets the Java Class which represents the entity.
	 * @param javaClass the Java Class of the entity.
	 */
	public void setJavaClass(String javaClass) {
		this.javaClass = javaClass;
	}
	
	/**
	 * Sets the OWL Class which represents the entity.
	 * @param ontologyClass the OWL Class of the entity.
	 */
	public void setOntologyClass(String ontologyClass) {
		this.ontologyClass = ontologyClass;
	}
	
	/**
	 * Sets the properties of the entity.
	 * @param propertyItems list of property items of the entity.
	 */
	public void setPropertyItems(List<PropertyItem> propertyItems) {
		this.propertyItems = propertyItems;
	}
	
	/**
	 * Validates if the entity is valid for its use in LinkedTagWorld.
	 * @return True if it is valid, False if not.
	 */
	public boolean validate() {
		if (this.ontologyClass == "") {
			return false;
		}
		return true;
	}
	
	/**
	 * Gets the main property which renders the links properly.
	 * @return the main property of entity. Returns null if no main property is defined.
	 */
	public PropertyItem getMainPropertyItem() {
		for (PropertyItem item : this.propertyItems) {
			if (item.getIsMain())
				return item;
		}
		return null;
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
