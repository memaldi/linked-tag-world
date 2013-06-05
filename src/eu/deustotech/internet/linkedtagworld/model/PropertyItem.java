package eu.deustotech.internet.linkedtagworld.model;

public class PropertyItem {
	private String identifier = "";
	private Boolean isLinkable = false;
	private Boolean isClickable = false;
	private Boolean isMain = false;
	private String ontologyProperty = "";
	private String datatype = "";
	private String language = "";
	
	public String getIdentifier() {
		return identifier;
	}
	public Boolean getIsLinkable() {
		return isLinkable;
	}
	public Boolean getIsMain() {
		return isMain;
	}
	public String getOntologyProperty() {
		return ontologyProperty;
	}
	public String getDatatype() {
		return datatype;
	}
	public String getLanguage() {
		return language;
	}
	public Boolean getIsClickable() {
		return isClickable;
	}
	public void setIdentifier(String identifier) {
		this.identifier = identifier;
	}
	public void setIsLinkable(Boolean isLinkable) {
		this.isLinkable = isLinkable;
	}
	public void setIsMain(Boolean isMain) {
		this.isMain = isMain;
	}
	public void setOntologyProperty(String ontologyProperty) {
		this.ontologyProperty = ontologyProperty;
	}
	public void setDatatype(String datatype) {
		this.datatype = datatype;
	}
	public void setLanguage(String language) {
		this.language = language;
	}
	public void setIsClickable(Boolean isClicable) {
		this.isClickable = isClicable;
	}
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
