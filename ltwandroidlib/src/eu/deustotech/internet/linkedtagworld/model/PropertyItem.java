package eu.deustotech.internet.linkedtagworld.model;

/**
 * Representation of an entity property in LinkedTagWorld.
 * @author jon
 *
 */
public class PropertyItem {
	private String identifier = "";
	private Boolean isLinkable = false;
	private Boolean isClickable = false;
	private Boolean isMain = false;
	private String ontologyProperty = "";
	private String datatype = "";
	private String language = "";
	
	/**
	 * Returns the identifier of the property.
	 * @return the identifier of the property.
	 */
	public String getIdentifier() {
		return identifier;
	}
	
	/**
	 * Returns if the property instead of representing a literal, links to a Class.
	 * @return True if links to a Class, False if not.
	 */
	public Boolean getIsLinkable() {
		return isLinkable;
	}
	
	/**
	 * Returns if the property is the main property of the class.
	 * @return True if property is the main property of the class, False if not.
	 */
	public Boolean getIsMain() {
		return isMain;
	}
	
	/**
	 * Returns the OWL Property Class which represents the entity.
	 * @return the OWL Property Class of the entity.
	 */
	public String getOntologyProperty() {
		return ontologyProperty;
	}
	
	/**
	 * Returns the <a href="http://www.w3.org/TR/xmlschema-2/">XSD Datatype</a> of the entity.
	 * @return the XSD Datatype of the entity.
	 */
	public String getDatatype() {
		return datatype;
	}
	
	/**
	 * Returns the <a target="_blank" href="http://www.loc.gov/standards/iso639-2/php/code_list.php">ISO 639-1</a> language code of the entity.
	 * @return the language code of the entity.
	 */
	public String getLanguage() {
		return language;
	}
	
	/**
	 * Returns if a linkable property can be clicked to retrieve information about the target entity.
	 * @return True if isClickable, False if not.
	 */
	public Boolean getIsClickable() {
		return isClickable;
	}
	
	/**
	 * Sets the identifier of the property.
	 * @param identifier the identifier of the property.
	 */
	public void setIdentifier(String identifier) {
		this.identifier = identifier;
	}
	/**
	 * Sets if the property instead of representing a literal, links to a Class.
	 * @param isLinkable True if links to a Class, False if not.
	 */
	public void setIsLinkable(Boolean isLinkable) {
		this.isLinkable = isLinkable;
	}
	
	/**
	 * Sets if the property is the main property of the class.
	 * @param isMain True if property is the main property of the class, False if not.
	 */
	public void setIsMain(Boolean isMain) {
		this.isMain = isMain;
	}
	
	/**
	 * Sets the OWL Property Class which represents the entity.
	 * @param ontologyProperty the OWL Property Class of the entity.
	 */
	public void setOntologyProperty(String ontologyProperty) {
		this.ontologyProperty = ontologyProperty;
	}
	
	/**
	 * Sets the <a href="http://www.w3.org/TR/xmlschema-2/">XSD Datatype</a> of the entity.
	 * @param datatype the datatype of the entity.
	 */
	public void setDatatype(String datatype) {
		this.datatype = datatype;
	}
	
	/**
	 * Sets the <a target="_blank" href="http://www.loc.gov/standards/iso639-2/php/code_list.php">ISO 639-1</a> language code of the entity.
	 * @param language the language code of the entity.
	 */
	public void setLanguage(String language) {
		this.language = language;
	}
	
	/**
	 * Sets if a linkable property can be clicked to retrieve information about the target entity.
	 * @param isClickable True if isClickable, False if not.
	 */
	public void setIsClickable(Boolean isClickable) {
		this.isClickable = isClickable;
	}
	
	/**
	 * Validates if the entity is valid for its use in LinkedTagWorld.
	 * @return True if it is valid, False if not.
	 */
	public boolean validate() {
		if (this.identifier == "" || this.ontologyProperty == "") {
			return false;
		}
		return true;
	}
	
	@Override 
	public String toString() {
		StringBuilder result = new StringBuilder();
	    String NEW_LINE = System.getProperty("line.separator");

	    result.append(" 	 " + this.getClass().getName() + " Object {" + NEW_LINE);
	    result.append("		  Identifier: " + identifier + NEW_LINE);
	    result.append(" 	  Ontology Property: " + ontologyProperty + NEW_LINE);
	    result.append(" 	  Linkable: " + isLinkable + NEW_LINE);
	    result.append(" 	  Clickable: " + isClickable + NEW_LINE);
	    result.append(" 	  Main: " + isMain + NEW_LINE);
	    if (datatype != "")
	    	result.append(" 	  Datatype: " + datatype + NEW_LINE);
	    if (language != "")
	    	result.append(" 	  Language: " + language + NEW_LINE);
	    
		return result.toString();		
	}
	
}
